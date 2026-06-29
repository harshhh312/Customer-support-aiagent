"""
Entry point for the Customer Support Agent API.
Run with:  python run.py
"""
import os
from dotenv import load_dotenv

# Load .env before anything else so env vars are available to all modules
load_dotenv()

import uvicorn

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
