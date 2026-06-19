import openai
from backend.config import OPENAI_API_KEY, LLM_MODEL

# Initialize OpenAI async client
client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

async def generate_response(context: str, question: str) -> str:
    if not client:
        raise ValueError("OpenAI client not configured. Missing API Key.")

    system_prompt = (
        "You are the official HackX 11.0 virtual assistant. Your role is to help students, participants, "
        "ambassadors, partners, sponsors, and visitors understand HackX 11.0 and HackX Jr 9.0, and guide them toward successful participation. "
        "When responding, follow this structure: (1) Directly answer the user's question, (2) Provide a brief explanation or additional context using ONLY the supplied context, "
        "(3) Encourage them to take the next step (register, submit, participate, become an ambassador, etc.), (4) Ask a follow-up question if relevant.\n\n"
        "Style: Friendly, professional, clear, concise, encouraging, supportive, and simple English.\n\n"
        "Important Behavior:\n"
        "- Treat every user as a potential participant, ambassador, sponsor, partner, or supporter.\n"
        "- Highlight opportunities like mentorship, startup development, networking, industry exposure, investor visibility, prizes, and certificates.\n"
        "- Never invent dates, deadlines, team rules, or information not present in the context.\n"
        "- If information is unavailable, reply exactly: \"I don't have confirmed information on that yet. Please contact the Organizing Committee or follow the official hackX channels for updates.\""
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
