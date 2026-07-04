import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_API_KEYS_STR = os.getenv("OPENAI_API_KEYS", os.getenv("OPENAI_API_KEY", ""))
OPENAI_API_KEYS = [k.strip() for k in OPENAI_API_KEYS_STR.split(",") if k.strip()]

LLM_MODEL = "llama-3.3-70b-versatile"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# Initialize supabase client
supabase: Client = (
    create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
)
