import openai
from backend.config import OPENAI_API_KEY, LLM_MODEL

# Initialize OpenAI async client
client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

async def generate_response(context: str, question: str) -> str:
    if not client:
        raise ValueError("OpenAI client not configured. Missing API Key.")

    system_prompt = (
        "You are the official HackX 11.0 virtual assistant. Your role is to help users by providing exact, factual information based on the context.\n\n"
        "CRITICAL RULES FOR RESPONDING:\n"
        "1. Be extremely concise. Provide the direct answer in as few words as possible.\n"
        "2. Do NOT give unsolicited advice, suggestions, or \"encouragement\".\n"
        "3. Do NOT ask follow-up questions.\n"
        "4. Do NOT explain why something is ideal (e.g. \"it's important to have a balanced team\"). Just state the rule.\n"
        "5. Never invent dates, deadlines, team rules, or information not present in the context.\n"
        "6. If information is unavailable, reply exactly: \"I don't have confirmed information on that yet. Please contact the Organizing Committee.\""
    )

    prompt = f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"

    response = await client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        temperature=0.0,
        max_tokens=300
    )
    return response.choices[0].message.content.strip()
