"""Provider-agnostic LLM wrapper with JSON parsing and retry logic."""
import json
import re
import sys
from typing import Dict, Any
from backend.config import LLM_PROVIDER, LLM_API_KEY, LLM_MODEL


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences from response text."""
    # Match ```json ... ``` or ``` ... ```
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
        # Try stripping code fences
        cleaned = _strip_code_fences(text)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON after retry: {e}")


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

    return PROVIDER_MAP[provider](system, user, max_tokens, temperature)


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