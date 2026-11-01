"""API client for Scheme Saathi backend."""
import os
import requests
from typing import Optional, Dict, Any, List

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
LLM_TIMEOUT = 60
DEFAULT_TIMEOUT = 15


def _post(endpoint: str, **kwargs) -> Dict[str, Any]:
    """POST request with timeout and error handling."""
    timeout = kwargs.pop("timeout", DEFAULT_TIMEOUT)
    try:
        response = requests.post(
            f"{BACKEND_URL}{endpoint}",
            timeout=timeout,
            **kwargs
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        return {"error": "The AI is busy, try again in a minute"}
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to backend. Is it running?"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"Server error: {e.response.status_code}"}
    except Exception as e:
        return {"error": str(e)}


def _post_json(endpoint: str, data: Dict[str, Any], timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    """POST JSON request."""
    return _post(endpoint, json=data, timeout=timeout)


def _post_file(endpoint: str, files: Dict[str, Any], data: Dict[str, Any] = None, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    """POST file upload request."""
    return _post(endpoint, files=files, data=data, timeout=timeout)


def analyze(text: str, language: str, profile_override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Analyze text and find matching schemes."""
    data = {"text": text, "language": language}
    if profile_override:
        data["profile_override"] = profile_override
    return _post_json("/api/analyze", data, timeout=LLM_TIMEOUT)


def chat(question: str, profile: Dict[str, Any], language: str,
         history: List[Dict[str, str]], matched_scheme_ids: List[str]) -> Dict[str, Any]:
    """Follow-up chat with matched schemes context."""
    data = {
        "question": question,
        "profile": profile,
        "language": language,
        "history": history,
        "matched_scheme_ids": matched_scheme_ids
    }
    return _post_json("/api/chat", data, timeout=LLM_TIMEOUT)


def explain_pdf(file_bytes: bytes, language: str) -> Dict[str, Any]:
    """Explain a PDF document."""
    files = {"file": ("document.pdf", file_bytes, "application/pdf")}
    data = {"language": language}
    return _post_file("/api/explain-pdf", files=files, data=data, timeout=LLM_TIMEOUT)


def stt(audio_bytes: bytes, language: str) -> Dict[str, Any]:
    """Speech to text."""
    files = {"audio": ("audio.wav", audio_bytes, "audio/wav")}
    data = {"language": language}
    return _post_file("/api/stt", files=files, data=data)


def tts(text: str, language: str) -> Dict[str, Any]:
    """Text to speech - returns MP3 bytes or error dict."""
    import logging
    logger = logging.getLogger(__name__)

    # Debug: print what we're sending
    logger.info(f"TTS request: language={language!r}, text_length={len(text)}, text_preview={text[:100]!r}")

    try:
        response = requests.post(
            f"{BACKEND_URL}/api/tts",
            json={"text": text, "language": language},
            timeout=DEFAULT_TIMEOUT
        )
        # Debug: print response status and headers
        logger.info(f"TTS response: status={response.status_code}, content_type={response.headers.get('content-type')}, content_length={len(response.content)}")
        response.raise_for_status()
        return {"audio": response.content, "content_type": "audio/mpeg"}
    except requests.exceptions.Timeout:
        return {"error": "Audio is unavailable right now"}
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to backend"}
    except requests.exceptions.HTTPError as e:
        # Debug: print error response
        logger.error(f"TTS HTTP error: status={e.response.status_code}, body={e.response.text[:500]!r}")
        if e.response.status_code == 503:
            return {"error": "Audio is unavailable right now"}
        if e.response.status_code == 400:
            try:
                return {"error": e.response.json().get("detail", "Invalid request")}
            except Exception:
                return {"error": "Invalid request"}
        return {"error": f"Server error: {e.response.status_code}"}
    except Exception as e:
        logger.exception(f"TTS unexpected error: {e}")
        return {"error": str(e)}


def official_source(scheme_id: str, language: str) -> Dict[str, Any]:
    """Fetch and summarize the official scheme page."""
    return _post_json("/api/official-source", {"scheme_id": scheme_id, "language": language}, timeout=30)