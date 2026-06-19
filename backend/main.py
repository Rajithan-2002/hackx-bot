import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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

from fastapi.staticfiles import StaticFiles

app = FastAPI(title="HackX Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to hackx.lk in production
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "HackX Chatbot API is running! Visit /health for status."}

app.mount("/assets", StaticFiles(directory=os.path.join(os.path.dirname(__file__), '..', 'widget', 'assets')), name="assets")

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None

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

@app.get("/widget.js")
async def widget_js():
    widget_path = os.path.join(os.path.dirname(__file__), '..', 'widget', 'widget.js')
    if os.path.exists(widget_path):
        headers = {"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}
        return FileResponse(widget_path, media_type="application/javascript", headers=headers)
    raise HTTPException(status_code=404, detail="widget.js not found")

@app.get("/widget.css")
async def widget_css():
    widget_path = os.path.join(os.path.dirname(__file__), '..', 'widget', 'widget.css')
    if os.path.exists(widget_path):
        headers = {"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}
        return FileResponse(widget_path, media_type="text/css", headers=headers)
    raise HTTPException(status_code=404, detail="widget.css not found")

@app.get("/avatar.png")
async def avatar():
    avatar_path = os.path.join(os.path.dirname(__file__), '..', 'widget', 'avatar.png')
    if os.path.exists(avatar_path):
        return FileResponse(avatar_path, media_type="image/png")
    raise HTTPException(status_code=404, detail="avatar.png not found")
