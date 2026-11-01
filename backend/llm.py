"""Provider-agnostic LLM wrapper with JSON parsing, retry logic, and disk caching."""
import json
import re
import sys
import time
import hashlib
import os
import traceback
from pathlib import Path
from typing import Dict, Any, Optional
from backend.config import LLM_PROVIDER, LLM_API_KEY, LLM_MODEL


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
        error_data = json.loads(error_text)
        retry_info = error_data.get("details", [])
        for detail in retry_info:
            if detail.get("@type", "").endswith("RetryInfo"):
                delay_str = detail.get("retryDelay", "")
                # Parse "40423s" format
                if delay_str.endswith("s"):
                    return int(delay_str[:-1])
    except Exception:
        pass
    return None


def _call_with_retry(
    call_func,
    system: str,
    user: str,
    max_tokens: int,
    temperature: float,
    max_retries: int = 3
) -> Dict[str, Any]:
    """Call LLM with retry on 429 errors."""
    last_error = None

    for attempt in range(max_retries):
        try:
            return call_func(system, user, max_tokens, temperature)
        except Exception as e:
            last_error = e
            error_str = str(e)

            # Check if it's a 429 error
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                retry_delay = _extract_retry_delay(error_str)
                if retry_delay is not None and attempt < max_retries - 1:
                    sleep_time = retry_delay + 1
                    print(f"Rate limited. Sleeping for {sleep_time}s before retry {attempt + 1}/{max_retries}...", file=sys.stderr)
                    time.sleep(sleep_time)
                    continue

            # For other errors or last retry, raise
            if attempt == max_retries - 1:
                raise

            # Small delay for other transient errors
            time.sleep(1)

    raise last_error


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

    provider = LLM_PROVIDER.lower()
    if provider not in PROVIDER_MAP:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")

    provider_func = PROVIDER_MAP[provider]
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


def _call_anthropic(system: str, user: str, max_tokens: int, temperature: float = 0.0) -> Dict[str, Any]:
    """Call Anthropic Claude API."""
    import anthropic
    client = anthropic.Anthropic(api_key=LLM_API_KEY)
    response = client.messages.create(
        model=LLM_MODEL,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system,
        messages=[{"role": "user", "content": user}]
    )
    return _parse_json_with_retry(response.content[0].text)


def _call_gemini(system: str, user: str, max_tokens: int, temperature: float = 0.0) -> Dict[str, Any]:
    """Call Google Gemini API using google-genai."""
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=LLM_API_KEY)
    response = client.models.generate_content(
        model=LLM_MODEL,
        contents=f"{system}\n\n{user}",
        config=types.GenerateContentConfig(temperature=temperature, max_output_tokens=max_tokens)
    )
    return _parse_json_with_retry(response.text)


def _call_openai(system: str, user: str, max_tokens: int, temperature: float = 0.0) -> Dict[str, Any]:
    """Call OpenAI API."""
    from openai import OpenAI
    client = OpenAI(api_key=LLM_API_KEY)
    response = client.chat.completions.create(
        model=LLM_MODEL,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]
    )
    return _parse_json_with_retry(response.choices[0].message.content)


PROVIDER_MAP = {
    "anthropic": _call_anthropic,
    "gemini": _call_gemini,
    "openai": _call_openai,
}


def call_text(system: str, user: str, max_tokens: int = 1500, temperature: float = 0.3) -> str:
    """
    Call LLM with system and user prompts, return plain text (no JSON parsing).

    Args:
        system: System prompt
        user: User prompt
        max_tokens: Maximum tokens for response
        temperature: Temperature for generation (default 0.3 for natural language)

    Returns:
        Plain text response

    Raises:
        ValueError: If provider not supported
    """
    provider = LLM_PROVIDER.lower()

    if provider not in PROVIDER_MAP:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider}. Supported: {list(PROVIDER_MAP.keys())}")

    if not LLM_API_KEY:
        raise ValueError("LLM_API_KEY not set in environment")

    # Check cache first
    cache_key = _get_cache_key(system, user, LLM_MODEL, temperature)
    if _should_use_cache():
        cached = _load_from_cache(cache_key)
        if cached is not None:
            print(f"Cache hit for key {cache_key[:8]}...", file=sys.stderr)
            # Cache stores JSON, but we want text. If cached is dict, extract text
            if isinstance(cached, dict):
                return cached.get("answer", cached.get("translated_text", str(cached)))
            return str(cached)

    # Call with retry logic - need a text-returning version of provider
    def call_text_func(sys_prompt, usr_prompt, max_tok, temp):
        provider = LLM_PROVIDER.lower()
        if provider == "anthropic":
            import anthropic
            client = anthropic.Anthropic(api_key=LLM_API_KEY)
            response = client.messages.create(
                model=LLM_MODEL,
                max_tokens=max_tok,
                temperature=temp,
                system=sys_prompt,
                messages=[{"role": "user", "content": usr_prompt}]
            )
            return response.content[0].text
        elif provider == "gemini":
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=LLM_API_KEY)
            response = client.models.generate_content(
                model=LLM_MODEL,
                contents=f"{sys_prompt}\n\n{usr_prompt}",
                config=types.GenerateContentConfig(temperature=temp, max_output_tokens=max_tok)
            )
            return response.text
        elif provider == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=LLM_API_KEY)
            response = client.chat.completions.create(
                model=LLM_MODEL,
                max_tokens=max_tok,
                temperature=temp,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": usr_prompt}
                ]
            )
            return response.choices[0].message.content
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    result = _call_with_retry(call_text_func, system, user, max_tokens, temperature)

    # Save to cache
    if _should_use_cache():
        _save_to_cache(cache_key, {"answer": result})

    return result


def call_json(system: str, user: str, max_tokens: int = 1500, temperature: float = 0.0) -> Dict[str, Any]:
    """
    Call LLM with system and user prompts, return parsed JSON.

    Args:
        system: System prompt
        user: User prompt
        max_tokens: Maximum tokens for response
        temperature: Temperature for generation (default 0.0 for deterministic extraction)

    Returns:
        Parsed JSON response as dict

    Raises:
        ValueError: If provider not supported or JSON parsing fails
        NotImplementedError: If provider not implemented
    """
    provider = LLM_PROVIDER.lower()

    if provider not in PROVIDER_MAP:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider}. Supported: {list(PROVIDER_MAP.keys())}")

    if not LLM_API_KEY:
        raise ValueError("LLM_API_KEY not set in environment")

    # Check cache first
    cache_key = _get_cache_key(system, user, LLM_MODEL, temperature)
    if _should_use_cache():
        cached = _load_from_cache(cache_key)
        if cached is not None:
            print(f"Cache hit for key {cache_key[:8]}...", file=sys.stderr)
            return cached

    # Call with retry logic
    provider_func = PROVIDER_MAP[provider]
    result = _call_with_retry(provider_func, system, user, max_tokens, temperature)

    # Save to cache
    if _should_use_cache():
        _save_to_cache(cache_key, result)

    return result


if __name__ == "__main__":
    # Quick test: python -m backend.llm "say hello in JSON"
    if len(sys.argv) > 1:
        user_prompt = " ".join(sys.argv[1:])
        system_prompt = "Respond ONLY with valid JSON. No markdown, no code fences, no explanation."
        try:
            result = call_json(system_prompt, user_prompt, max_tokens=200)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("Usage: python -m backend.llm \"your prompt here\"")


if __name__ == "__main__":
    # Quick test: python -m backend.llm "say hello in JSON"
    if len(sys.argv) > 1:
        user_prompt = " ".join(sys.argv[1:])
        system_prompt = "Respond ONLY with valid JSON. No markdown, no code fences, no explanation."
        try:
            result = call_json(system_prompt, user_prompt, max_tokens=200)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("Usage: python -m backend.llm \"your prompt here\"")