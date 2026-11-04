"""API client for Scheme Saathi backend - direct function calls (no HTTP)."""
import os
import json
import logging
from typing import Optional, Dict, Any, List

from backend.extract import extract_profile
from backend.match import match_schemes
from backend.explain import explain_results, select_results, answer_chat, explain_pdf
from backend.rag import search as rag_search, get_scheme, list_schemes
from backend.stt import transcribe as stt_transcribe
from backend.tts import synthesize as tts_synthesize
from backend.pdf_reader import extract_text as pdf_extract_text
from backend.rules import check_all_schemes
from backend.config import SCHEMES_FILE, LLM_API_KEY
from google import genai
import requests

# For official_source - still need to fetch live
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
DEFAULT_TIMEOUT = 15
LLM_TIMEOUT = 60


def _post(endpoint: str, **kwargs) -> Dict[str, Any]:
    """POST request with timeout and error handling (fallback for official_source)."""
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
    """Analyze text and find matching schemes - direct backend call."""
    try:
        # 1. Extract profile from text
        profile, missing = extract_profile(text, debug=False)
        profile_dict = profile.model_dump()

        # Merge profile_override (override wins)
        if profile_override:
            profile_dict.update(profile_override)

        # 2. Match schemes using Python rules
        results = match_schemes(profile_dict, text)

        # 3. Select top results
        selected = select_results(results, profile_dict, text)

        # 4. Explain results (1 LLM call)
        explained_results, summary_text = explain_results(selected, profile_dict, language)

        # Prepare response
        results_list = []
        for r in explained_results:
            results_list.append({
                "scheme_id": r.scheme_id,
                "scheme": r.scheme,
                "eligible": r.eligible,
                "reason": r.reason,
                "benefit": r.benefit,
                "documents": r.documents,
                "how_to_apply": r.how_to_apply,
                "official_link": r.official_link,
                "source_quote": r.source_quote,
                "explanation": r.explanation,
            })

        # Compute missing fields from selected schemes
        needed_facts = set()
        for r in explained_results:
            scheme = next((s for s in json.load(open(SCHEMES_FILE)) if s["id"] == r.scheme_id), None)
            if scheme:
                rules = scheme.get("rules", {})
                if rules.get("gender") is not None:
                    needed_facts.add("gender")
                if rules.get("min_age") is not None or rules.get("max_age") is not None:
                    needed_facts.add("age")
                if rules.get("max_income") is not None:
                    needed_facts.add("annual_income")
                if rules.get("states"):
                    needed_facts.add("state")
                if rules.get("occupations"):
                    needed_facts.add("occupation")
                if rules.get("needs_land"):
                    needed_facts.add("land_acres")
                if rules.get("categories") and scheme.get("requires_verification"):
                    needed_facts.add("caste_category")

        missing_fields = [f for f in needed_facts if profile_dict.get(f) is None]

        return {
            "profile": profile_dict,
            "missing_fields": missing_fields,
            "results": results_list,
            "summary_text": summary_text,
            "language": language,
            "disclaimer": "Verify at official portal before applying."
        }

    except Exception as e:
        logging.exception("Error in analyze")
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            return {"error": "The AI is busy, please try again in a minute"}
        return {"error": str(e)}


def chat(question: str, profile: Dict[str, Any], language: str,
         history: List[Dict[str, str]], matched_scheme_ids: List[str]) -> Dict[str, Any]:
    """Follow-up chat with matched schemes context - direct backend call."""
    try:
        answer, sources, translation_failed = answer_chat(
            question=question,
            profile=profile,
            language=language,
            history=history,
            matched_scheme_ids=matched_scheme_ids
        )
        return {
            "answer": answer,
            "sources": sources,
            "translation_failed": translation_failed
        }
    except Exception as e:
        logging.exception("Error in chat")
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            return {"error": "The AI is busy, please try again in a minute"}
        return {"error": str(e)}


def explain_pdf(file_bytes: bytes, language: str) -> Dict[str, Any]:
    """Explain a PDF document - direct backend call."""
    try:
        text = pdf_extract_text(file_bytes)
        summary, key_points, who_is_affected, deadlines = explain_pdf(text, language)
        return {
            "summary": summary,
            "key_points": key_points,
            "who_is_affected": who_is_affected,
            "deadlines": deadlines,
            "language": language
        }
    except Exception as e:
        logging.exception("Error in explain_pdf")
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            return {"error": "The AI is busy, please try again in a minute"}
        return {"error": str(e)}


def stt(audio_bytes: bytes, language: str) -> Dict[str, Any]:
    """Speech to text - direct backend call."""
    try:
        text = stt_transcribe(audio_bytes, language)
        return {"text": text, "language": language}
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        logging.exception("Error in stt")
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            return {"error": "Audio is unavailable right now"}
        return {"error": str(e)}


def tts(text: str, language: str) -> Dict[str, Any]:
    """Text to speech - direct backend call."""
    import logging
    logger = logging.getLogger(__name__)

    # Debug: print what we're sending
    logger.info(f"TTS request: language={language!r}, text_length={len(text)}, text_preview={text[:100]!r}")

    try:
        audio_bytes = tts_synthesize(text, language)
        return {"audio": audio_bytes, "content_type": "audio/mpeg"}
    except Exception as e:
        logger.exception(f"TTS unexpected error: {e}")
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            return {"error": "Audio is unavailable right now"}
        return {"error": str(e)}


def official_source(scheme_id: str, language: str) -> Dict[str, Any]:
    """Fetch and summarize the official scheme page - still uses HTTP to backend or direct call."""
    # Try to use the direct function if available
    try:
        from backend.explain import call_text
        from backend.rag import get_scheme

        scheme = get_scheme(scheme_id)
        if not scheme:
            return {"error": "Scheme not found", "success": False}

        official_link = scheme.get("official_link", "")
        if not official_link:
            return {
                "scheme_id": scheme_id,
                "scheme_name": scheme.get("name", "Unknown"),
                "summary": "",
                "source_url": "",
                "success": False,
                "error": "No official link available for this scheme."
            }

        # Fetch the page
        import requests
        import re

        try:
            response = requests.get(official_link, timeout=10, headers={
                "User-Agent": "Mozilla/5.0 (compatible; SchemeSaathi/1.0)"
            })
            response.raise_for_status()
            html_content = response.text
        except requests.exceptions.Timeout:
            return {
                "scheme_id": scheme_id,
                "scheme_name": scheme.get("name", "Unknown"),
                "summary": "",
                "source_url": official_link,
                "success": False,
                "error": "The official portal took too long to respond. Please try again later or visit the portal directly."
            }
        except requests.exceptions.RequestException as e:
            return {
                "scheme_id": scheme_id,
                "scheme_name": scheme.get("name", "Unknown"),
                "summary": "",
                "source_url": official_link,
                "success": False,
                "error": f"Could not fetch the official portal: {str(e)}"
            }

        # Strip HTML tags
        text_content = re.sub(r"<[^>]+>", " ", html_content)
        text_content = re.sub(r"\s+", " ", text_content).strip()
        text_content = text_content[:8000]

        # Summarize with LLM
        from backend.config import LANGUAGE_NAMES
        lang_name = LANGUAGE_NAMES.get(language, "English")

        system_prompt = f"""You are a government scheme information assistant.
Summarize the official scheme page content in {lang_name} ({language} script).
Focus on: what the scheme offers, who is eligible, how to apply, key benefits.
Use simple words, short sentences. Max 5 sentences.
Keep scheme names in English. Do not add information not in the source."""

        user_prompt = f"""Scheme: {scheme.get('name', '')}
Official URL: {official_link}

Page content (extracted):
{text_content}

Summarize in {lang_name} ({language} script):"""

        summary = call_text(system_prompt, user_prompt, max_tokens=400, temperature=0.3)

        return {
            "scheme_id": scheme_id,
            "scheme_name": scheme.get("name", "Unknown"),
            "summary": summary,
            "source_url": official_link,
            "success": True,
            "error": None
        }

    except Exception as e:
        logging.exception("Error in official_source")
        return {
            "scheme_id": scheme_id,
            "scheme_name": "Unknown",
            "summary": "",
            "source_url": "",
            "success": False,
            "error": "Failed to generate summary. Please visit the official portal directly."
        }