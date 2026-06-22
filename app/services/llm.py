import openai
import itertools
import os
from app.core.config import OPENAI_API_KEYS, LLM_MODEL, GROQ_BASE_URL

# Initialize OpenAI async clients pointing to Groq
clients = [openai.AsyncOpenAI(api_key=key, base_url=GROQ_BASE_URL) for key in OPENAI_API_KEYS]
client_cycle = itertools.cycle(clients) if clients else None

def get_client():
    if not client_cycle:
        raise ValueError("OpenAI clients not configured. Missing API Keys.")
    return next(client_cycle)

# In-memory context caching
CONTEXT_CACHE = {}

def load_competition_context(competition_id: str) -> str:
    if competition_id in CONTEXT_CACHE:
        return CONTEXT_CACHE[competition_id]
        
    data_dir = os.path.join(os.path.dirname(__file__), "..", "core", "data")
    if competition_id == "hackxjr":
        file_path = os.path.join(data_dir, "hackx_jr_faq.md")
    else:
        # For HackX, we might want to combine timeline and hackx_faq, but for now we'll stick to hackx_faq
        # We can actually combine them if we want to provide timeline data as well.
        faq_path = os.path.join(data_dir, "hackx_faq.md")
        timeline_path = os.path.join(data_dir, "timeline.md")
        
        content = ""
        try:
            with open(faq_path, "r", encoding="utf-8") as f:
                content += f.read() + "\n\n"
            if os.path.exists(timeline_path):
                with open(timeline_path, "r", encoding="utf-8") as f:
                    content += f.read()
        except Exception as e:
            print(f"Error loading context for {competition_id}: {e}")
            
        CONTEXT_CACHE[competition_id] = content
        return content

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            CONTEXT_CACHE[competition_id] = content
            return content
    except Exception as e:
        print(f"Error loading context for {competition_id}: {e}")
        return ""


async def generate_response(competition_id: str, question: str, history: str = "") -> str:
    client = get_client()
    context = load_competition_context(competition_id)

    system_prompt = (
        "You are the official virtual assistant for HackX and HackX Jr.\n"
        "Your role is to help students, participants, ambassadors, partners, sponsors, and visitors understand the competition and guide them toward successful participation.\n"
        "You have been provided with the complete, official rulebook, timeline, and FAQ document for the competition below.\n\n"
        "CRITICAL STRICT GROUNDING RULES:\n"
        "1. You MUST ONLY answer questions using the information provided in the context below.\n"
        "2. If the user asks a question that is NOT covered in the provided context (e.g. general programming help, math, history, how to make an app, etc.), YOU MUST REFUSE TO ANSWER.\n"
        "3. Do not invent, hallucinate, or rely on outside general knowledge to answer questions.\n"
        "4. If the information is missing from the context, respond exactly with: 'I don't have confirmed information on that yet. Please contact the Organizing Committee or follow the official channels for updates.'\n\n"
        "Response Style:\n"
        "- Friendly, professional, and encouraging.\n"
        "- Clear and concise.\n"
        "- Formatted using bullet points (-) for readability.\n"
        "- Use relevant emojis!\n"
        "- NEVER use Markdown headings (like #, ##, or ###). Just use bold text or bullet points instead.\n"
        "- DO NOT ask follow-up questions. End cleanly.\n\n"
        "Competition Rulebook & Context:\n"
        f"{context}\n"
    )

    prompt = f"Question: {question}\n"
    if history:
        prompt = f"Conversation History:\n{history}\n\n" + prompt

    response = await client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
        max_tokens=500,
    )
    return response.choices[0].message.content.strip()
