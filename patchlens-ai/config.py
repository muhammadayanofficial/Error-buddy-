"""Application configuration. Secrets come from environment variables only."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv is optional at import time
    load_dotenv = None

BASE_DIR = Path(__file__).resolve().parent
if load_dotenv:
    load_dotenv(BASE_DIR / ".env")

LANGUAGES = ["Python", "JavaScript", "TypeScript", "Java", "C#", "C++", "Go", "Rust", "PHP", "SQL", "Other"]
MAX_CODE_CHARS = 20000
MAX_ERROR_CHARS = 8000


class Config:
    DATABASE = str(BASE_DIR / "data" / "patchlens.db")


def get_api_key():
    return os.environ.get("GEMINI_API_KEY", "").strip()


def get_model():
    return os.environ.get("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
