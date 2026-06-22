import openai
import itertools
from app.core.config import OPENAI_API_KEYS, EMBED_MODEL

# Initialize OpenAI async clients
clients = [openai.AsyncOpenAI(api_key=key) for key in OPENAI_API_KEYS]
client_cycle = itertools.cycle(clients) if clients else None

def get_client():
    if not client_cycle:
        raise ValueError("OpenAI clients not configured. Missing API Keys.")
    return next(client_cycle)


async def get_embedding(text: str) -> list[float]:
    client = get_client()
    response = await client.embeddings.create(input=text, model=EMBED_MODEL)
    return response.data[0].embedding
