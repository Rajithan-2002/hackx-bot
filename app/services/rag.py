import json
import os
import re
import traceback
from app.core.config import (
    supabase,
    VECTOR_THRESHOLD,
    LLM_THRESHOLD,
    ENABLE_LLM_FALLBACK,
    ENABLE_RETRIEVAL_ONLY_MODE,
)
from app.services.embeddings import get_embedding
from app.services.llm import generate_response
from app.services.domain_guard import is_domain_valid
from app.services.cache import get_cached_response, set_cached_response
from app.utils.analytics import log_chat

# In-memory session context: session_id -> list of {"role": "user"|"assistant", "content": str}
SESSIONS = {}
MAX_SESSION_HISTORY = 6  # Last 3 turn pairs (3 user, 3 assistant)

# Load aliases
ALIASES_FILE = os.path.join(
    os.path.dirname(__file__), "..", "core", "data", "aliases.json"
)
try:
    with open(ALIASES_FILE, "r") as f:
        aliases_map = json.load(f)
except Exception:
    aliases_map = {}

# Regex for common greetings including repeated trailing characters and typical typos
GREETING_REGEX = re.compile(
    r"^(hi+y*a*|hey+|hello+|greetings+|good\s+morn?in?g|good\s+morining|morning|mornin|good\s+afternoon|good\s+evening|howdy|yo+|sup+|whats\s+up|what\'s\s+up|hiya|hola|bonjour|hallo|how\s+are\s+you|are\s+you\s+there|anyone\s+there)([\s,!.?]+|$)",
    re.IGNORECASE,
)


def cosine_similarity(v1, v2):
    dot_product = sum(a * b for a, b in zip(v1, v2))
    magnitude1 = sum(a * a for a in v1) ** 0.5
    magnitude2 = sum(b * b for b in v2) ** 0.5
    if not magnitude1 or not magnitude2:
        return 0.0
    return dot_product / (magnitude1 * magnitude2)


def clean_chunk_text(text: str) -> str:
    # Remove markdown heading markers at the beginning of lines, e.g. "### Registration\n"
    text = re.sub(r"^#+\s+.*\n?", "", text).strip()
    return text


def get_session_history(session_id: str | None) -> str:
    if not session_id or session_id not in SESSIONS:
        return ""
    history = []
    for msg in SESSIONS[session_id]:
        role_label = "User" if msg["role"] == "user" else "Assistant"
        history.append(f"{role_label}: {msg['content']}")
    return "\n".join(history)


def update_session_history(session_id: str | None, role: str, content: str):
    if not session_id:
        return
    if session_id not in SESSIONS:
        SESSIONS[session_id] = []
    SESSIONS[session_id].append({"role": role, "content": content})
    if len(SESSIONS[session_id]) > MAX_SESSION_HISTORY:
        SESSIONS[session_id] = SESSIONS[session_id][-MAX_SESSION_HISTORY:]


def strip_greeting_prefix(question: str) -> tuple[str, bool]:
    """
    Checks if a question starts with a greeting keyword.
    Returns: (remaining_question, did_greet)
    """
    q_clean = question.strip()
    match = GREETING_REGEX.match(q_clean)
    if match:
        remaining = q_clean[match.end() :].strip(" \t\n\r.!,?")
        return remaining, True
    return question, False


def resolve_aliases(question: str) -> str:
    q_lower = question.lower().strip()
    # Direct match in map
    if q_lower in aliases_map:
        return aliases_map[q_lower]
    # Check if keyword substitution works
    for key, val in aliases_map.items():
        if key in q_lower:
            return q_lower.replace(key, val)
    return q_lower


async def answer_question(question: str, competition_id: str, session_id: str | None = None) -> dict:
    """
    6-tier RAG-powered pipeline with OpenAI failure resilience
    """
    # GREETING DETECTION (Smooth flow for greetings without LLM calls)
    remaining_q, did_greet = strip_greeting_prefix(question)
    if did_greet:
        if not remaining_q:
            answer = "Hello! I am HackX Assistant, your virtual guide for HackX 11.0 and HackX Jr 9.0. How can I help you today?"
            log_chat(question, answer, "GREETING", 1.0)
            update_session_history(session_id, "user", question)
            update_session_history(session_id, "assistant", answer)
            return {"answer": answer, "source": "greeting", "tier": 0}
        else:
            # Clean compound greetings (e.g. "Hey, when is registration?") and use query remainder
            question = remaining_q

    # TIER 2: Response Cache Check
    cached = get_cached_response(question, competition_id)
    if cached:
        log_chat(question, cached, "CACHE", 1.0)
        update_session_history(session_id, "user", question)
        update_session_history(session_id, "assistant", cached)
        return {"answer": cached, "source": "cache", "tier": 2}

    # TIER 3 & 4: Synonym & Exact FAQ Match
    resolved_query = resolve_aliases(question)
    if supabase:
        try:
            faq_result = supabase.table("faq_exact").select("*").eq("competition_id", competition_id).execute()
            for faq in faq_result.data:
                # FAQ matching targets the exact question and its defined aliases
                aliases = [faq["question"].lower().strip()] + [
                    a.lower().strip() for a in (faq.get("aliases") or [])
                ]
                if (question.lower().strip() in aliases) or (resolved_query in aliases):
                    answer = faq["answer"]
                    log_chat(question, answer, "FAQ", 1.0)
                    set_cached_response(question, answer, competition_id, "faq_exact")
                    update_session_history(session_id, "user", question)
                    update_session_history(session_id, "assistant", answer)
                    return {"answer": answer, "source": "faq_exact", "tier": 4}
        except Exception as e:
            print(f"Error checking exact FAQs: {e}")

    # TIER 5: Vector Similarity Search
    retrieved_chunks = []
    top_similarity = 0.0
    embedding_failed = False

    try:
        embedding = await get_embedding(question)
        if supabase:
            vector_result = supabase.rpc(
                "match_documents",
                {
                    "query_embedding": embedding,
                    "match_threshold": LLM_THRESHOLD,  # retrieve anything above low threshold
                    "match_count": 5,
                    "filter_competition_id": competition_id
                },
            ).execute()
            retrieved_chunks = vector_result.data or []

            # Python in-memory similarity fallback (runs if RPC is empty OR returns low-confidence matches < 0.50)
            if not retrieved_chunks or retrieved_chunks[0]["similarity"] < 0.50:
                all_chunks = (
                    supabase.table("document_chunks")
                    .select("id, chunk_text, metadata, embedding")
                    .execute()
                )
                if all_chunks.data:
                    scored_chunks = []
                    for chunk in all_chunks.data:
                        if chunk.get("metadata", {}).get("competition_id") != competition_id:
                            continue
                        if chunk.get("embedding"):
                            emb_val = chunk["embedding"]
                            if isinstance(emb_val, str):
                                import json

                                try:
                                    emb_val = json.loads(emb_val)
                                except Exception:
                                    emb_val = [
                                        float(x) for x in emb_val.strip("[]").split(",")
                                    ]

                            sim = cosine_similarity(emb_val, embedding)
                            if sim >= LLM_THRESHOLD:
                                scored_chunks.append(
                                    {
                                        "id": chunk["id"],
                                        "chunk_text": chunk["chunk_text"],
                                        "metadata": chunk["metadata"],
                                        "similarity": sim,
                                    }
                                )
                    scored_chunks.sort(key=lambda x: x["similarity"], reverse=True)

                    # Override if Python in-memory search found a higher-confidence match
                    if scored_chunks and (
                        not retrieved_chunks
                        or scored_chunks[0]["similarity"]
                        > retrieved_chunks[0]["similarity"]
                    ):
                        retrieved_chunks = scored_chunks[:5]

            if retrieved_chunks:
                top_similarity = retrieved_chunks[0]["similarity"]
    except Exception as e:
        print(f"Embedding or Vector search failed: {e}")
        embedding_failed = True

    # Check Vector Match Confidence
    if not retrieved_chunks or top_similarity < LLM_THRESHOLD:
        if is_domain_valid(question):
            answer = "I don't have confirmed information on that yet. Please contact the Organizing Committee or follow the official hackX channels for updates."
            log_chat(question, answer, "UNKNOWN", top_similarity)
            return {"answer": answer, "source": "unknown", "tier": 5}
        else:
            answer = (
                "Sorry, I can only help with HackX 11.0 and HackX Jr 9.0 information."
            )
            log_chat(question, answer, "OUT_OF_SCOPE", top_similarity)
            return {"answer": answer, "source": "domain_guard", "tier": 1}

    # EXACT SECTION MATCH OVERRIDE:
    # If the user's query exactly matches a section header (e.g. "Timeline", "Contact"),
    # return it directly to save cost and increase performance.
    for chunk in retrieved_chunks:
        section_name = chunk["metadata"].get("section", "")
        if section_name and question.lower().strip() == section_name.lower().strip():
            chunk_text = chunk["chunk_text"]
            formatted_answer = clean_chunk_text(chunk_text)
            if formatted_answer:
                source_meta = chunk["metadata"] or {}
                source = source_meta.get("source", "HackX Rulebook")

                log_chat(
                    question,
                    formatted_answer,
                    "VECTOR_EXACT_SECTION",
                    chunk["similarity"],
                )
                set_cached_response(question, formatted_answer, competition_id, "vector_search")
                update_session_history(session_id, "user", question)
                update_session_history(session_id, "assistant", formatted_answer)
                return {"answer": formatted_answer, "source": source, "tier": 5}

    # High Confidence Match (>= VECTOR_THRESHOLD)
    if top_similarity >= VECTOR_THRESHOLD:
        valid_chunk = None
        formatted_answer = ""
        for chunk in retrieved_chunks:
            if chunk["similarity"] >= VECTOR_THRESHOLD:
                cleaned = clean_chunk_text(chunk["chunk_text"])
                if cleaned:
                    valid_chunk = chunk
                    formatted_answer = cleaned
                    break

        if valid_chunk:
            source_meta = valid_chunk["metadata"] or {}
            source = source_meta.get("source", "HackX Rulebook")

            log_chat(question, formatted_answer, "VECTOR", valid_chunk["similarity"])
            set_cached_response(question, formatted_answer, competition_id, "vector_search")
            update_session_history(session_id, "user", question)
            update_session_history(session_id, "assistant", formatted_answer)
            return {"answer": formatted_answer, "source": source, "tier": 5}

    # TIER 6: LLM Synthesis or RETRIEVAL_ONLY Fallback
    context = "\n\n".join(
        [
            f"Source: {c['metadata'].get('source', 'HackX')} | Section: {c['metadata'].get('section', '')}\nContent: {c['chunk_text']}"
            for c in retrieved_chunks
        ]
    )

    if ENABLE_LLM_FALLBACK and not embedding_failed:
        try:
            # Build conversation context
            history_str = get_session_history(session_id)
            prompt_context = context
            if history_str:
                prompt_context = f"Conversation History:\n{history_str}\n\nSupplied Context:\n{context}"

            answer = await generate_response(prompt_context, question)
            log_chat(question, answer, "LLM", top_similarity)
            set_cached_response(question, answer, competition_id, "llm_synthesis")
            update_session_history(session_id, "user", question)
            update_session_history(session_id, "assistant", answer)
            return {"answer": answer, "source": "llm_generated", "tier": 6}
        except Exception as e:
            print(f"LLM synthesis failed: {e}")
            traceback.print_exc()
            # If LLM fails, fall through to retrieval-only mode if enabled

    # Fallback to RETRIEVAL_ONLY Mode
    if ENABLE_RETRIEVAL_ONLY_MODE and retrieved_chunks:
        cleaned_bullets = []
        for chunk in retrieved_chunks:
            cleaned = clean_chunk_text(chunk["chunk_text"])
            if cleaned:
                cleaned_bullets.append(f"• {cleaned}")

        if cleaned_bullets:
            bullets_str = "\n".join(cleaned_bullets[:3])
            fallback_answer = (
                f"I found the following relevant information:\n\n{bullets_str}"
            )

            log_chat(question, fallback_answer, "RETRIEVAL_ONLY", top_similarity)
            update_session_history(session_id, "user", question)
            update_session_history(session_id, "assistant", fallback_answer)
            return {"answer": fallback_answer, "source": "retrieved_chunks", "tier": 6}

    # If all fallback mechanisms fail
    if is_domain_valid(question):
        answer = "I don't have confirmed information on that yet. Please contact the Organizing Committee or follow the official hackX channels for updates."
        log_chat(question, answer, "UNKNOWN", top_similarity)
        return {"answer": answer, "source": "unknown", "tier": 5}
    else:
        answer = "Sorry, I can only help with HackX 11.0 and HackX Jr 9.0 information."
        log_chat(question, answer, "OUT_OF_SCOPE", top_similarity)
        return {"answer": answer, "source": "domain_guard", "tier": 1}
