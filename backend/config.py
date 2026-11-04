"""Configuration management - loads environment variables and constants."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file (for local development)
load_dotenv()


def _get_secret(key: str, default: str = "") -> str:
    """Get secret from env var, falling back to st.secrets (Streamlit Cloud)."""
    # First check environment variable
    value = os.getenv(key)
    if value:
        return value

    # Then try Streamlit secrets
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass

    return default


# LLM Configuration (from env / Streamlit Cloud secrets)
LLM_PROVIDER = _get_secret("LLM_PROVIDER", "google")
LLM_API_KEY = _get_secret("LLM_API_KEY", "")
LLM_MODEL = _get_secret("LLM_MODEL", "gemini-2.5-flash")

# App Configuration
BACKEND_URL = _get_secret("BACKEND_URL", "http://localhost:8000")

# STT/TTS Providers
STT_PROVIDER = _get_secret("STT_PROVIDER", "gemini")
STT_MODEL = _get_secret("STT_MODEL", "gemini-2.5-flash")
TTS_PROVIDER = _get_secret("TTS_PROVIDER", "gtts")

# Data paths
DATA_DIR = Path(__file__).parent.parent / "data"
SCHEMES_FILE = DATA_DIR / "schemes.json"
PDFS_DIR = DATA_DIR / "pdfs"

# Index file
INDEX_FILE = DATA_DIR / "index.npz"

# Cache directories (created at runtime)
TTS_CACHE_DIR = Path(__file__).parent.parent / "tts_cache"
LLM_CACHE_DIR = Path(__file__).parent.parent / "llm_cache"

# Supported languages
SUPPORTED_LANGUAGES = ["en", "hi", "mr", "ta", "bn", "te", "gu", "kn"]