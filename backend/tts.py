"""Text-to-speech module using gTTS."""
import hashlib
import os
import re
from pathlib import Path
from urllib.parse import urlparse

# Language code mapping: our codes -> gTTS codes
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

# Cache directory
CACHE_DIR = Path(__file__).parent.parent / "tts_cache"
CACHE_DIR.mkdir(exist_ok=True)

MAX_TEXT_LENGTH = 1500


def _clean_text(text: str) -> str:
    """
    Clean text for TTS: strip URLs (keep site name), markdown symbols, emojis, ₹ signs.
    """
    # Replace URLs with just the domain name
    def replace_url(match):
        url = match.group(0)
        try:
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path.split('/')[0]
            # Remove www. prefix
            domain = domain.replace('www.', '')
            return domain
        except Exception:
            return "link"

    # Pattern for URLs
    url_pattern = r'https?://[^\s]+'
    text = re.sub(url_pattern, replace_url, text)

    # Strip markdown symbols: *, _, ~, `, #, >, [, ], (, ), <, >
    markdown_chars = r'[*_~`#>\\[\\]()<>]'
    text = re.sub(markdown_chars, '', text)

    # Strip emojis (Unicode ranges for emojis)
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"  # dingbats
        "\U000024C2-\U0001F251"  # enclosed characters
        "]+", flags=re.UNICODE
    )
    text = emoji_pattern.sub('', text)

    # Strip ₹ symbols
    text = text.replace('₹', '').replace('Rs.', '').replace('Rs', '').replace('INR', '')

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def _limit_text(text: str, max_length: int = MAX_TEXT_LENGTH) -> str:
    """Limit text to max_length, cutting at sentence end."""
    if len(text) <= max_length:
        return text

    # Find the last sentence end within the limit
    truncated = text[:max_length]
    last_period = truncated.rfind('.')
    last_question = truncated.rfind('?')
    last_exclamation = truncated.rfind('!')

    last_sentence_end = max(last_period, last_question, last_exclamation)

    if last_sentence_end > max_length * 0.5:  # Only cut at sentence if we keep at least half
        return truncated[:last_sentence_end + 1].strip()

    return truncated.strip()


def _get_cache_path(text: str, language: str) -> Path:
    """Generate cache file path from hash of (text + language)."""
    cache_key = f"{text}|{language}"
    cache_hash = hashlib.sha256(cache_key.encode('utf-8')).hexdigest()[:16]
    return CACHE_DIR / f"{cache_hash}.mp3"


def synthesize(text: str, language: str) -> bytes:
    """
    Synthesize text to speech using gTTS, with caching.

    Args:
        text: Text to synthesize
        language: Language code (mr, hi, en, ta, bn, te, gu, kn)

    Returns:
        MP3 audio bytes

    Raises:
        ValueError: If language is not supported
        RuntimeError: If gTTS fails (e.g., network error)
    """
    if not text or not text.strip():
        raise ValueError("Empty text provided")

    # Map our language code to gTTS language code
    gtts_lang = LANGUAGE_MAP.get(language.lower())
    if gtts_lang is None:
        raise ValueError(f"Unsupported language: {language}. Supported: {list(LANGUAGE_MAP.keys())}")

    # Clean text for TTS
    cleaned_text = _clean_text(text)
    cleaned_text = _limit_text(cleaned_text)

    # If cleaning resulted in empty text, fall back to original (trimmed)
    if not cleaned_text:
        cleaned_text = text.strip()
        if not cleaned_text:
            raise ValueError("Text is empty after cleaning")

    # Check cache
    cache_path = _get_cache_path(cleaned_text, language)
    if cache_path.exists():
        return cache_path.read_bytes()

    # Generate with gTTS
    try:
        from gtts import gTTS
        import io

        tts = gTTS(text=cleaned_text, lang=gtts_lang, slow=False)

        # Save to bytes buffer
        buffer = io.BytesIO()
        tts.write_to_fp(buffer)
        audio_bytes = buffer.getvalue()

        # Save to cache
        cache_path.write_bytes(audio_bytes)

        return audio_bytes

    except Exception as e:
        # Friendly error for common failures (network, etc.)
        if "network" in str(e).lower() or "connection" in str(e).lower() or "timeout" in str(e).lower() or "rate limit" in str(e).lower() or "429" in str(e):
            raise RuntimeError("Audio is unavailable right now") from e
        raise RuntimeError(f"TTS generation failed: {e}") from e