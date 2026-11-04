"""Speech-to-text module using Gemini audio transcription."""
import tempfile
from pathlib import Path
from typing import Optional

from backend.config import LLM_API_KEY
from google import genai

# Language code mapping: our codes -> Gemini language codes
LANGUAGE_MAP = {
    "mr": "mr",   # Marathi
    "hi": "hi",   # Hindi
    "en": "en",   # English
    "ta": "ta",   # Tamil
    "bn": "bn",   # Bengali
    "te": "te",   # Telugu
    "gu": "gu",   # Gujarati
    "kn": "kn",   # Kannada
}

# Limits
MAX_AUDIO_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_AUDIO_DURATION = 60  # seconds (approximate, we check size as proxy)


def transcribe(audio_bytes: bytes, language: str) -> str:
    """
    Transcribe audio bytes to text using Gemini.

    Args:
        audio_bytes: Raw audio data (WAV format expected)
        language: Language code (mr, hi, en, ta, bn, te, gu, kn)

    Returns:
        Transcribed text string

    Raises:
        ValueError: If language is not supported, audio is empty, too large, or too long
    """
    if not audio_bytes:
        raise ValueError("Empty audio data provided")

    # Check size limit
    if len(audio_bytes) > MAX_AUDIO_SIZE:
        raise ValueError(
            f"Audio file too large ({len(audio_bytes) / 1024 / 1024:.1f} MB). "
            f"Maximum size is {MAX_AUDIO_SIZE / 1024 / 1024} MB. "
            f"Please record a shorter clip."
        )

    # Map our language code to whisper language code
    gemini_lang = LANGUAGE_MAP.get(language.lower())
    if gemini_lang is None:
        raise ValueError(
            f"Unsupported language: {language}. "
            f"Supported: {list(LANGUAGE_MAP.keys())}"
        )

    # Write audio bytes to a temporary file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
        tmp_file.write(audio_bytes)
        tmp_path = tmp_file.name

    try:
        client = genai.Client(api_key=LLM_API_KEY)

        # Upload the audio file
        audio_file = client.files.upload(file=tmp_path)

        # Generate transcription
        prompt = (
            f"Transcribe this audio exactly in the original language ({gemini_lang}). "
            f"Do not translate. Return only the text."
        )

        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=[prompt, audio_file]
        )

        text = response.text.strip()
        return text

    except Exception as e:
        raise ValueError(f"Transcription failed: {str(e)}")

    finally:
        # Clean up temp file
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass