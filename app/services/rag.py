import re
import traceback
from app.services.llm import generate_response
from app.services.cache import get_cached_response, set_cached_response
from app.utils.analytics import log_chat

# In-memory session context: session_id -> list of {"role": "user"|"assistant", "content": str}
SESSIONS = {}
MAX_SESSION_HISTORY = 6  # Last 3 turn pairs (3 user, 3 assistant)

# Regex for common greetings including repeated trailing characters and typical typos
GREETING_REGEX = re.compile(
    r"^(hi+y*a*|hey+|hello+|greetings+|good\s+morn?in?g|good\s+morining|morning|mornin|good\s+afternoon|good\s+evening|howdy|yo+|sup+|whats\s+up|what\'s\s+up|hiya|hola|bonjour|hallo|how\s+are\s+you|are\s+you\s+there|anyone\s+there)([\s,!.?]+|$)",
    re.IGNORECASE,
)

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


async def answer_question(question: str, competition_id: str, session_id: str | None = None) -> dict:
    """
    Simplified Context Stuffing Pipeline
    """
    # TIER 0: GREETING DETECTION (Smooth flow for greetings without LLM calls)
    remaining_q, did_greet = strip_greeting_prefix(question)
    if did_greet:
        if not remaining_q:
            comp_name = "HackX" if competition_id == "hackx" else "HackX Jr"
            answer = f"Hello! I am the {comp_name} Assistant. How can I help you today?"
            log_chat(question, answer, "GREETING", 1.0)
            update_session_history(session_id, "user", question)
            update_session_history(session_id, "assistant", answer)
            return {"answer": answer, "source": "greeting", "tier": 0}
        else:
            # Clean compound greetings (e.g. "Hey, when is registration?") and use query remainder
            question = remaining_q

    # TIER 1: Response Cache Check
    cached = get_cached_response(question, competition_id)
    if cached:
        log_chat(question, cached, "CACHE", 1.0)
        update_session_history(session_id, "user", question)
        update_session_history(session_id, "assistant", cached)
        return {"answer": cached, "source": "cache", "tier": 1}

    # TIER 2: Direct LLM Call with Context Stuffing
    try:
        history_str = get_session_history(session_id)
        
        answer = await generate_response(competition_id, question, history_str)
        
        log_chat(question, answer, "LLM", 1.0)
        set_cached_response(question, answer, competition_id, "llm_synthesis")
        update_session_history(session_id, "user", question)
        update_session_history(session_id, "assistant", answer)
        
        return {"answer": answer, "source": "llm_generated", "tier": 2}
        
    except Exception as e:
        print(f"LLM synthesis failed: {e}")
        traceback.print_exc()
        answer = "I'm currently experiencing technical difficulties connecting to my brain. Please try again in a moment."
        log_chat(question, answer, "ERROR", 0.0)
        return {"answer": answer, "source": "error", "tier": 2}
