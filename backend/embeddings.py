import openai
from backend.config import OPENAI_API_KEY, EMBED_MODEL

# Initialize OpenAI async client
client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)

async def get_embedding(text: str) -> list[float]:
    response = await client.embeddings.create(
        input=text,
        model=EMBED_MODEL
    )
    return response.data[0].embedding
