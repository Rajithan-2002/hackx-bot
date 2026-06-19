import hashlib
from datetime import datetime
from backend.config import supabase

def get_hash(text: str) -> str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def get_cached_response(question: str) -> str | None:
    if not supabase:
        return None
    q_hash = get_hash(question.lower().strip())
    try:
        result = supabase.table("chat_cache").select("*").eq("question_hash", q_hash).execute()
        if result.data:
            usage = result.data[0].get("usage_count", 1) + 1
            # Update usage stats
            supabase.table("chat_cache").update({
                "usage_count": usage,
                "last_used": datetime.utcnow().isoformat()
            }).eq("question_hash", q_hash).execute()
            return result.data[0]["answer"]
    except Exception:
        pass
    return None

def set_cached_response(question: str, answer: str, source: str = "cache"):
    if not supabase:
        return
    q_hash = get_hash(question.lower().strip())
    try:
        supabase.table("chat_cache").insert({
            "question_hash": q_hash,
            "answer": answer,
            "source": source
        }).execute()
    except Exception:
        pass
