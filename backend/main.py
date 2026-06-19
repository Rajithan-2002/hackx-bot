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

from fastapi.responses import HTMLResponse

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HackX 11.0 | Mockup</title>
    <style>
        body { margin: 0; font-family: 'Inter', system-ui, sans-serif; background: #080808; color: white; min-height: 100vh; }
        header { padding: 20px 40px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #222; }
        .logo { font-size: 24px; font-weight: bold; color: #7C3AED; }
        nav { display: flex; gap: 20px; }
        nav a { color: #ccc; text-decoration: none; }
        nav a:hover { color: white; }
        .hero { text-align: center; padding: 100px 20px; }
        h1 { font-size: 64px; margin: 0; background: linear-gradient(to right, #7C3AED, #c084fc); -webkit-background-clip: text; color: transparent; }
        p { font-size: 20px; color: #aaa; max-width: 600px; margin: 20px auto; }
        .btn { background: #7C3AED; color: white; border: none; padding: 12px 32px; font-size: 18px; border-radius: 8px; cursor: pointer; }
    </style>
</head>
<body>
    <header>
        <div class="logo">HackX 11.0</div>
        <nav><a href="#">About</a><a href="#">Timeline</a><a href="#">Sponsors</a><a href="#">Contact</a></nav>
    </header>
    <div class="hero">
        <h1>Sri Lanka's Premier Hackathon</h1>
        <p>Join the 11th edition of HackX and build the future. Registration opens soon!</p>
        <button class="btn">Register Now</button>
    </div>
    <!-- HackX Chatbot Widget Injection -->
    <script src="/widget.js"></script>
</body>
</html>"""

@app.get("/")
@app.get("/api")
async def root():
    return HTMLResponse(content=HTML_CONTENT)

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
