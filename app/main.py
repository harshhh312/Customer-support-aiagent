import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import your modules
from .agent import process_query
from .conversation_memory import clear_conversation

app = FastAPI(title="Abstergo Support AI", version="1.0.0")

# --- CORS (Allow Streamlit to talk to FastAPI) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
# 🩺 HEALTH CHECK
# ========================================
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "Abstergo Support AI"}

# ========================================
# 🧑‍⚖️ JUDGE STATUS
# ========================================
@app.get("/api/hitl/status")
async def get_judge_status():
    judge_enabled = os.getenv("USE_LLM_JUDGE", "True").lower() == "true"
    return {"mode": judge_enabled}

# ========================================
# 🗑️ CLEAR HISTORY
# ========================================
@app.post("/clear_history/{email}")
async def clear_history(email: str):
    clear_conversation(email)
    return {"message": f"Conversation history cleared for {email}", "email": email}

# ========================================
# 💬 CHAT ENDPOINT
# ========================================
@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        reply = process_query(request.email, request.message)
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ========================================
# 🚀 RUN (for local development)
# ========================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)