from google import genai
import os
from dotenv import load_dotenv
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
_loaded = load_dotenv(_env_path, override=True)
print(f"[startup] .env path: {_env_path}")
print(f"[startup] .env file exists: {os.path.exists(_env_path)}")
print(f"[startup] load_dotenv() succeeded: {_loaded}")
_gk = os.environ.get("GEMINI_API_KEY", "")
_ok = os.environ.get("OPENAI_API_KEY", "")
print(f"[startup] GEMINI_API_KEY loaded: {bool(_gk)} (len={len(_gk)})")
print(f"[startup] OPENAI_API_KEY loaded: {bool(_ok)} (len={len(_ok)})")
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

for model in client.models.list():
    print(model.name)