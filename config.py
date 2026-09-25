"""
Loads API keys from a local .env file (never uploaded/synced anywhere).
Copy .env.example to .env and fill in your keys.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the SAME FOLDER as this file, regardless of what directory
# you happen to run `streamlit run app.py` from. Without this, load_dotenv()
# only looks in the current working directory — if you launch Streamlit from
# a different folder (e.g. a parent directory, or via an IDE's own working
# directory), it silently finds nothing and every key looks "missing" even
# though your .env file is filled in correctly.
load_dotenv(Path(__file__).resolve().parent / ".env")

# Which AI provider to use for tailoring. "groq" is free (no card), fast,
# and the default. "ollama" is free and fully local/offline. "gemini" is
# free (no card). "anthropic" is paid but highest quality.
PROVIDER = os.getenv("PROVIDER", "groq")

# --- Groq (free, no credit card - https://console.groq.com/keys) ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
# NOTE: llama-3.3-70b-versatile moved to Groq's Enterprise-only tier and will
# 404 on a free account. openai/gpt-oss-120b (or the faster/cheaper
# openai/gpt-oss-20b) are the current free-developer-tier models.
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# --- Ollama (free, fully local - https://ollama.com) ---
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

# --- Google Gemini (free tier, no credit card - https://aistudio.google.com/apikey) ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# --- Anthropic (paid, highest quality - optional) ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")

# --- Adzuna job search (free - https://developer.adzuna.com/) ---
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "")
ADZUNA_COUNTRY = os.getenv("ADZUNA_COUNTRY", "in")

# --- Startup diagnostic (prints to your terminal, never the browser) ---
_env_path = Path(__file__).resolve().parent / ".env"
if not _env_path.exists():
    print(f"[config] WARNING: no .env file found at {_env_path} — "
          f"copy .env.example to .env in that exact folder and fill in your keys.")
else:
    _found = {
        "GROQ_API_KEY": bool(GROQ_API_KEY), "GEMINI_API_KEY": bool(GEMINI_API_KEY),
        "ANTHROPIC_API_KEY": bool(ANTHROPIC_API_KEY),
        "ADZUNA_APP_ID": bool(ADZUNA_APP_ID), "ADZUNA_APP_KEY": bool(ADZUNA_APP_KEY),
    }
    print(f"[config] Loaded .env from {_env_path}")
    print(f"[config] Keys present: {[k for k, v in _found.items() if v] or 'NONE'}")
    _missing = [k for k, v in _found.items() if not v]
    if _missing:
        print(f"[config] Keys NOT set (fine to ignore if you don't use that provider): {_missing}")
