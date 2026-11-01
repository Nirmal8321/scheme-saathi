"""Configuration management - loads environment variables and constants."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-5-5")

# App Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# STT/TTS Providers
STT_PROVIDER = os.getenv("STT_PROVIDER", "faster_whisper")
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "gtts")

# Data paths
DATA_DIR = Path(__file__).parent.parent / "data"
SCHEMES_FILE = DATA_DIR / "schemes.json"
PDFS_DIR = DATA_DIR / "pdfs"

# ChromaDB - use /tmp for reliable disk I/O
CHROMA_DIR = Path("/tmp/chroma_db")

# TTS cache
TTS_CACHE_DIR = Path(__file__).parent.parent / "tts_cache"

# Supported languages
SUPPORTED_LANGUAGES = ["en", "hi", "mr", "ta", "bn", "te", "gu", "kn"]