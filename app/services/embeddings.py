import openai
from app.core.config import OPENAI_API_KEY, EMBED_MODEL

# Initialize OpenAI async client
client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

async def get_embedding(text: str) -> list[float]:
    if not client:
        raise ValueError("OpenAI client not configured. Missing API Key.")
    response = await client.embeddings.create(
        input=text,
        model=EMBED_MODEL
    )
    return response.data[0].embedding
