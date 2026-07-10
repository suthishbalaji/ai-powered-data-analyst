import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
_loaded = load_dotenv(_env_path, override=True)
print(f"[startup] .env path: {_env_path}")
print(f"[startup] .env file exists: {os.path.exists(_env_path)}")
print(f"[startup] load_dotenv() succeeded: {_loaded}")
_gk = os.environ.get("GEMINI_API_KEY", "")
_grk = os.environ.get("GROQ_API_KEY", "")
_ok = os.environ.get("OPENAI_API_KEY", "")
print(f"[startup] GEMINI_API_KEY loaded: {bool(_gk)} (len={len(_gk)})")
print(f"[startup] GROQ_API_KEY loaded: {bool(_grk)} (len={len(_grk)})")
print(f"[startup] OPENAI_API_KEY loaded: {bool(_ok)} (len={len(_ok)})")

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import router

app = FastAPI(
    title="AI-Powered Data Analyst API",
    description="FastAPI Backend for CSV uploads and AI queries",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/")
def read_root():
    return {"message": "AI-Powered Data Analyst API is running."}

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
