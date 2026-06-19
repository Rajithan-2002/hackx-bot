import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend.config import (
    supabase,
    OPENAI_API_KEY,
    ENABLE_LLM_FALLBACK,
    ENABLE_RETRIEVAL_ONLY_MODE
)
from backend.rag import answer_question
from backend.rate_limit import check_rate_limit
from backend.llm import client as openai_client

app = FastAPI(title="HackX Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to hackx.lk in production
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None

@app.post("/api/chat")
@app.post("/chat")
async def chat(request: ChatRequest, fastapi_req: Request):
    # Enforce rate limit (30 requests / minute / IP)
    client_host = fastapi_req.client.host if fastapi_req.client else "127.0.0.1"
    check_rate_limit(client_host)

    if not request.message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    result = await answer_question(request.message, request.session_id)
    return {
        "answer": result["answer"],
        "source": result["source"],
        "tier": result["tier"]
    }

@app.get("/api/health")
@app.get("/health")
async def health():
    supabase_ok = False
    vector_ok = False
    cache_ok = False
    openai_ok = bool(openai_client and OPENAI_API_KEY)

    # Check Supabase, Vector Search, and Cache
    if supabase:
        try:
            supabase.table("faq_exact").select("id").limit(1).execute()
            supabase_ok = True
        except Exception:
            pass

        try:
            supabase.table("document_chunks").select("id").limit(1).execute()
            vector_ok = True
        except Exception:
            pass

        try:
            supabase.table("chat_cache").select("id").limit(1).execute()
            cache_ok = True
        except Exception:
            pass

    # Mode calculation
    mode = "standard"
    if not ENABLE_LLM_FALLBACK or not openai_ok:
        if ENABLE_RETRIEVAL_ONLY_MODE:
            mode = "retrieval_only"
        else:
            mode = "degraded"

    is_healthy = supabase_ok and (openai_ok or ENABLE_RETRIEVAL_ONLY_MODE)

    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "supabase": supabase_ok,
        "openai": openai_ok,
        "vector_search": vector_ok,
        "cache": cache_ok,
        "mode": mode
    }
