import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

EMBED_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-4o-mini"

# Similarity thresholds
EXACT_MATCH_THRESHOLD = 0.70
VECTOR_THRESHOLD = 0.70
LLM_THRESHOLD = 0.25

# Configuration Flags for testing/resilience
ENABLE_LLM_FALLBACK = os.getenv("ENABLE_LLM_FALLBACK", "True").lower() == "true"
ENABLE_RETRIEVAL_ONLY_MODE = (
    os.getenv("ENABLE_RETRIEVAL_ONLY_MODE", "True").lower() == "true"
)

# Domain Guard Configuration
DOMAIN_KEYWORDS = [
    "hackx",
    "hackx jr",
    "registration",
    "eligibility",
    "timeline",
    "venue",
    "judging",
    "sponsors",
    "rules",
    "submission",
    "team",
    "contact",
    "prize",
    "deadline",
    "member",
    "student",
    "submit",
    "idea",
    "proposal",
    "pitch",
    "video",
    "prototype",
    "workshop",
    "seminar",
    "challenge",
    "award",
    "cash",
    "certificate",
    "startup",
    "youtube",
    "link",
    "unlisted",
    "business",
    "innovation",
    "entrepreneur",
    "participate",
    "register",
    "join",
    "competition",
    "objective",
]

# Initialize supabase client
supabase: Client = (
    create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
)
