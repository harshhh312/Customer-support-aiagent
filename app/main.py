import os
from fastapi import FastAPI, HTTPException, Security, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# --- Rate Limiting ---
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# --- Your modules ---
from .agent import process_query
from .conversation_memory import clear_conversation
from .auth import verify_api_key

# --- App Initialization ---
app = FastAPI(title="Abstergo Support AI", version="1.0.0")

# --- Rate Limiter Setup ---
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- CORS (Allow Streamlit & Web UI) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to your domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========================================
# 📦 REQUEST MODELS
# ========================================
class ChatRequest(BaseModel):
    email: str
    message: str

# ========================================
# 🩺 HEALTH CHECK (Public)
# ========================================
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "Abstergo Support AI"}

# ========================================
# 🧑‍⚖️ JUDGE STATUS (Public)
# ========================================
@app.get("/api/hitl/status")
async def get_judge_status():
    judge_enabled = os.getenv("USE_LLM_JUDGE", "True").lower() == "true"
    return {"mode": judge_enabled}

# ========================================
# 🌐 STATIC FILES (Public)
# ========================================
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")

# ========================================
# 💬 CHAT ENDPOINT (Auth + Rate Limited)
# ========================================
@app.post("/chat")
@limiter.limit("20/minute")  # Max 20 requests per minute per IP
async def chat(request: Request, chat_request: ChatRequest, api_key: str = Security(verify_api_key)):
    """
    Process a customer query and return an AI-generated reply.
    Requires X-API-Key header.
    """
    try:
        result = process_query(chat_request.email, chat_request.message)
        return {"reply": result["reply"], "sentiment": result["sentiment"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ========================================
# 🗑️ CLEAR HISTORY (Auth + Rate Limited)
# ========================================
@app.post("/clear_history/{email}")
@limiter.limit("10/minute")  # Max 10 requests per minute per IP
async def clear_history(request: Request, email: str, api_key: str = Security(verify_api_key)):
    """
    Clears the conversation history for a specific user.
    Requires X-API-Key header.
    """
    clear_conversation(email)
    return {"message": f"Conversation history cleared for {email}", "email": email}

# ========================================
# 🚀 RUN (for local development)
# ========================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)