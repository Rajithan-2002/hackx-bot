from app.core.config import supabase

def log_chat(question: str, answer: str, route: str, confidence: float = 0.0):
    if not supabase:
        return
    try:
        supabase.table("chat_logs").insert({
            "question": question,
            "answer": answer,
            "route_used": route,
            "confidence": confidence
        }).execute()
    except Exception as e:
        print(f"Error logging chat: {e}")
        pass
