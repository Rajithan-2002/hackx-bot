import openai
import itertools
import os
from app.core.config import OPENAI_API_KEYS, LLM_MODEL, GROQ_BASE_URL

# Initialize OpenAI async clients pointing to Groq
clients = [
    openai.AsyncOpenAI(api_key=key, base_url=GROQ_BASE_URL) for key in OPENAI_API_KEYS
]
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
    content = ""

    if competition_id == "hackxjr":
        faq_path = os.path.join(data_dir, "hackx_jr_faq.md")
        timeline_path = os.path.join(data_dir, "hackx_jr_timeline.md")
        contact_path = os.path.join(data_dir, "hackxjr_contact_details.md")
    else:
        faq_path = os.path.join(data_dir, "hackx_faq.md")
        timeline_path = os.path.join(data_dir, "hackx_timeline.md")
        contact_path = os.path.join(data_dir, "hackx_contact_details.md")

    try:
        if os.path.exists(faq_path):
            with open(faq_path, "r", encoding="utf-8") as f:
                content += f.read() + "\n\n"
        if os.path.exists(timeline_path):
            with open(timeline_path, "r", encoding="utf-8") as f:
                content += f.read() + "\n\n"
        if os.path.exists(contact_path):
            with open(contact_path, "r", encoding="utf-8") as f:
                content += f.read()
    except Exception as e:
        print(f"Error loading context for {competition_id}: {e}")

    CONTEXT_CACHE[competition_id] = content
    return content


def load_system_prompt(competition_id: str, context: str) -> str:
    data_dir = os.path.join(os.path.dirname(__file__), "..", "core", "data")
    if competition_id == "hackxjr":
        prompt_path = os.path.join(data_dir, "system_prompt_hackxjr.txt")
    else:
        prompt_path = os.path.join(data_dir, "system_prompt_hackx.txt")

    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()
            return template.replace("{context}", context)
    except Exception as e:
        print(f"Error loading system prompt template: {e}")
        return f"You are the official virtual assistant. Competition Context:\n{context}"


async def generate_response(
    competition_id: str, question: str, history: str = ""
) -> str:
    context = load_competition_context(competition_id)
    system_prompt = load_system_prompt(competition_id, context)

    prompt = f"Question: {question}\n"
    if history:
        prompt = f"Conversation History:\n{history}\n\n" + prompt

    num_clients = len(clients) if clients else 0
    if num_clients == 0:
        raise ValueError("OpenAI clients not configured. Missing API Keys.")

    last_error = None
    for attempt in range(num_clients):
        client = get_client()
        try:
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
        except Exception as e:
            print(
                f"API Client attempt {attempt + 1}/{num_clients} failed with error: {e}"
            )
            last_error = e

    if last_error:
        raise last_error
    raise ValueError("All configured API clients failed to generate a response.")
