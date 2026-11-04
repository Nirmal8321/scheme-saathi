"""LLM wrapper using Google GenAI SDK (supports new AQ... keys)."""
import os
import json
import re
import sys
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
from google import genai
from backend.config import LLM_API_KEY, LLM_MODEL

_client = None

def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences from response text."""
    pattern = r'^```(?:json)?\s*\n?(.*?)\n?```$'
    match = re.match(pattern, text.strip(), re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def _parse_json_with_retry(text: str) -> Dict[str, Any]:
    """Parse JSON with one retry after stripping code fences."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        cleaned = _strip_code_fences(text)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON after retry: {e}")


def _get_cache_dir() -> Path:
    """Get the cache directory path."""
    cache_dir = Path("./llm_cache")
    cache_dir.mkdir(exist_ok=True)
    return cache_dir


def _get_cache_key(system: str, user: str, model: str, temperature: float) -> str:
    """Generate cache key from system+user+model+temperature."""
    content = f"{system}|{user}|{model}|{temperature}"
    return hashlib.sha256(content.encode()).hexdigest()


def _load_from_cache(cache_key: str) -> Optional[Dict[str, Any]]:
    """Load response from disk cache if exists."""
    cache_dir = _get_cache_dir()
    cache_file = cache_dir / f"{cache_key}.json"
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def _save_to_cache(cache_key: str, response: Dict[str, Any]) -> None:
    """Save response to disk cache."""
    cache_dir = _get_cache_dir()
    cache_file = cache_dir / f"{cache_key}.json"
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(response, f, ensure_ascii=False)
    except Exception:
        pass


def _should_use_cache() -> bool:
    """Check if caching is enabled via environment variable."""
    return os.getenv("LLM_CACHE", "false").lower() == "true"


def _extract_retry_delay(error_text: str) -> Optional[int]:
    """Extract retry delay in seconds from 429 error response."""
    try:
        # Try to parse as JSON first
        error_json = json.loads(error_text)
        if "error" in error_json and "details" in error_json["error"]:
            for detail in error_json["error"]["details"]:
                if "@type" in detail and "RetryInfo" in detail["@type"]:
                    retry_delay = detail.get("retryDelay", "0s")
                    return int(retry_delay.replace("s", ""))
    except Exception:
        pass
    return None


def get_client():
    """Get or create genai client (supports new AQ... keys)."""
    global _client
    if _client is None:
        _client = genai.Client(api_key=LLM_API_KEY)
    return _client


def call_text(system_prompt: str, user_prompt: str, max_tokens: int = 1000, temperature: float = 0.3) -> str:
    """Call LLM for text generation."""
    client = get_client()
    response = client.models.generate_content(
        model=LLM_MODEL,
        contents=f"{system_prompt}\n\n{user_prompt}",
        config=genai.types.GenerateContentConfig(max_output_tokens=max_tokens, temperature=temperature)
    )
    return response.text


def call_json(system_prompt: str, user_prompt: str, max_tokens: int = 2000, temperature: float = 0.3) -> dict:
    """Call LLM for JSON output."""
    client = get_client()
    response = client.models.generate_content(
        model=LLM_MODEL,
        contents=f"{system_prompt}\n\n{user_prompt}",
        config=genai.types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
            response_mime_type="application/json"
        )
    )
    return _parse_json_with_retry(response.text)


def translate_text(text: str, target_language: str, max_retries: int = 2) -> Dict[str, Any]:
    """
    Translate text to target language with retry logic for 429 errors.

    Args:
        text: Text to translate
        target_language: Target language code (en, hi, mr, etc.)
        max_retries: Maximum number of retries (default 2 = 1 retry)

    Returns:
        Dict with 'translated_text' and optionally 'translation_failed': true
    """
    lang_names = {
        "en": "English", "hi": "Hindi", "mr": "Marathi",
        "ta": "Tamil", "bn": "Bengali", "te": "Telugu",
        "gu": "Gujarati", "kn": "Kannada"
    }
    lang_name = lang_names.get(target_language, "English")

    system_prompt = f"""Translate the following text into {lang_names.get(target_language, 'English')} ({target_language} script).
Keep scheme names and portal names in English. Use simple words, short sentences.
Return ONLY the translated text, no JSON, no explanation."""

    user_prompt = f"Text to translate:\n{text}\n\nTarget language: {target_language} ({lang_names.get(target_language, 'English')})"

    last_error = None

    for attempt in range(max_retries):
        try:
            result = call_json(
                system_prompt + "\n\nRespond with just the translated text.",
                f"{user_prompt}",
                max_tokens=500,
                temperature=0.3
            )
            # call_json returns parsed JSON, but we want plain text
            if isinstance(result, dict):
                translated = result.get("answer", str(result))
            else:
                translated = str(result)
            return {"translated_text": translated.strip(), "translation_failed": False}
        except Exception as e:
            error_str = str(e)
            error_type = type(e).__name__
            print(f"Translation attempt {attempt + 1} failed: {error_type}: {error_str}", file=sys.stderr)

            # Check if it's a 429 error
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                retry_delay = _extract_retry_delay(error_str)
                if retry_delay is not None and attempt < max_retries - 1:
                    sleep_time = retry_delay + 1
                    print(f"Translation rate limited. Sleeping for {sleep_time}s before retry {attempt + 1}/{max_retries}...", file=sys.stderr)
                    time.sleep(sleep_time)
                    continue

            last_error = e
            if attempt == max_retries - 1:
                # Last attempt failed - return original text with failure flag
                print(f"Translation failed after {max_retries} attempts: {error_type}: {error_str}", file=sys.stderr)
                return {
                    "translated_text": f"[Translation failed] {text}",
                    "translation_failed": True,
                    "error_type": error_type,
                    "error_message": str(last_error)[:200]
                }

            # Small delay for other transient errors
            time.sleep(1)

    # Should not reach here, but just in case
    return {
        "translated_text": f"[Translation failed] {text}",
        "translation_failed": True,
        "error_type": type(last_error).__name__ if last_error else "Unknown",
        "error_message": str(last_error)[:200] if last_error else "Unknown error"
    }