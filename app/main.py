import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from app.core.config import (
    supabase,
    OPENAI_API_KEYS,
    ENABLE_LLM_FALLBACK,
    ENABLE_RETRIEVAL_ONLY_MODE,
)
from app.services.rag import answer_question
from app.middleware.rate_limit import limiter
from app.services.llm import clients as openai_clients
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

app = FastAPI(title="HackX Chatbot API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
@app.get("/api")
async def root():
    index_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "public", "index.html")
    )
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content)
    return HTMLResponse(content="<h1>Mockup not found</h1>", status_code=404)


class ChatRequest(BaseModel):
    message: str
    competition_id: str
    session_id: str | None = None


@app.post("/api/chat")
@app.post("/chat")
@limiter.limit("30/minute")
async def chat(chat_request: ChatRequest, request: Request):
    if not chat_request.message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    if not chat_request.competition_id:
        raise HTTPException(status_code=400, detail="Competition selection required")

    result = await answer_question(chat_request.message, chat_request.competition_id, chat_request.session_id)
    return {
        "answer": result["answer"],
        "source": result["source"],
        "tier": result["tier"],
    }


@app.get("/api/health")
@app.get("/health")
async def health():
    supabase_ok = False
    vector_ok = False
    cache_ok = False
    openai_ok = bool(openai_clients and OPENAI_API_KEYS)

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
        "mode": mode,
    }


# Mount static files so local testing can serve widget.js, widget.css, etc.
# Placed at the end so it doesn't override explicit routes like /

public_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "public"))
if os.path.exists(public_dir):
    app.mount("/", StaticFiles(directory=public_dir), name="public")
