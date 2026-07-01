from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .agent import process_query
from .memory import init_db
import uvicorn


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise resources on startup (DB tables, etc.)."""
    init_db()          # creates user_memory table if it doesn't exist
    yield
    # (shutdown logic goes here if needed)


app = FastAPI(title="Customer Support AI Agent", lifespan=lifespan)


class QueryRequest(BaseModel):
    email: str
    message: str


class QueryResponse(BaseModel):
    reply: str


@app.post("/chat", response_model=QueryResponse)
async def chat(request: QueryRequest):
    try:
        reply = process_query(request.email, request.message)
        return QueryResponse(reply=reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)