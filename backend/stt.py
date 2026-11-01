"""Speech-to-text module using faster-whisper."""
import os
import tempfile
from pathlib import Path
from typing import Optional

# Language code mapping: our codes -> whisper codes
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

# Global model instance (lazy-loaded)
_model: Optional["WhisperModel"] = None


def _get_model() -> "WhisperModel":
    """Get or create the faster-whisper model instance."""
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        model_size = os.getenv("STT_MODEL", "small")
        _model = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8"
        )
    return _model


def transcribe(audio_bytes: bytes, language: str) -> str:
    """
    Transcribe audio bytes to text using faster-whisper.

    Args:
        audio_bytes: Raw audio data (WAV format expected)
        language: Language code (mr, hi, en, ta, bn, te, gu, kn)

    Returns:
        Transcribed text string

    Raises:
        ValueError: If language is not supported or audio is empty
    """
    if not audio_bytes:
        raise ValueError("Empty audio data provided")

    # Map our language code to whisper language code
    whisper_lang = LANGUAGE_MAP.get(language.lower())
    if whisper_lang is None:
        raise ValueError(f"Unsupported language: {language}. Supported: {list(LANGUAGE_MAP.keys())}")

    model = _get_model()

    # Write audio bytes to a temporary file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
        tmp_file.write(audio_bytes)
        tmp_path = tmp_file.name

    try:
        # Transcribe with beam_size=5 and vad_filter=True
        segments, info = model.transcribe(
            tmp_path,
            language=whisper_lang,
            beam_size=5,
            vad_filter=True
        )

        # Join all segment texts
        text = " ".join(segment.text for segment in segments).strip()
        return text

    finally:
        # Clean up temp file
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass