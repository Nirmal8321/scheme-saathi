"""FastAPI application for Scheme Saathi backend."""
import os
import json
import logging
import re
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Literal

import requests

from backend.extract import extract_profile
from backend.match import match_schemes
from backend.explain import explain_results, select_results, answer_chat, explain_pdf
from backend.pdf_reader import extract_text
from backend.stt import transcribe
from backend.tts import synthesize

# Enable LLM cache by default
os.environ.setdefault("LLM_CACHE", "true")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Scheme Saathi API", version="1.0.0")

# Load schemes data
SCHEMES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "schemes.json")
with open(SCHEMES_PATH, "r", encoding="utf-8") as f:
    SCHEMES = json.load(f)
SCHEME_MAP = {s["id"]: s for s in SCHEMES}


# Pydantic models for request/response
class AnalyzeRequest(BaseModel):
    text: str
    language: Literal["en", "hi", "mr", "ta", "bn", "te", "gu", "kn"]
    profile_override: Optional[Dict[str, Any]] = None


class ChatRequest(BaseModel):
    question: str
    profile: Dict[str, Any]
    language: Literal["en", "hi", "mr", "ta", "bn", "te", "gu", "kn"]
    history: List[Dict[str, str]] = []


class AnalyzeResponse(BaseModel):
    profile: Dict[str, Any]
    missing_fields: List[str]
    results: List[Dict[str, Any]]
    summary_text: str
    language: str
    disclaimer: str = "Verify at official portal before applying."


class ChatResponse(BaseModel):
    answer: str
    sources: List[str]
    translation_failed: bool = False


class PdfExplainResponse(BaseModel):
    summary: str
    key_points: List[str]
    who_is_affected: str
    deadlines: List[str]
    language: str


class OfficialSourceRequest(BaseModel):
    scheme_id: str
    language: Literal["en", "hi", "mr", "ta", "bn", "te", "gu", "kn"]


class OfficialSourceResponse(BaseModel):
    scheme_id: str
    scheme_name: str
    summary: str
    source_url: str
    success: bool
    error: Optional[str] = None


class ErrorResponse(BaseModel):
    error: str


# Helper functions
def get_scheme_ids_for_profile(profile: Dict[str, Any]) -> List[str]:
    """Get matched scheme IDs for a profile using Python rules only (no LLM)."""
    from backend.rules import check_all_schemes
    results = check_all_schemes(profile, SCHEMES)
    return [r["scheme_id"] for r in results if r["verdict"] in ("yes", "maybe")]


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error. Please try again later."}
    )


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    """
    Main analysis endpoint: extract profile, match schemes, select top results, explain in language.
    Max 3 LLM calls per request (extract, match uses rules, explain uses 1 LLM call).
    """
    try:
        # 1. Extract profile from text
        profile, missing = extract_profile(request.text, debug=False)
        profile_dict = profile.model_dump()

        # Merge profile_override (override wins)
        if request.profile_override:
            profile_dict.update(request.profile_override)

        # 2. Match schemes using Python rules
        results = match_schemes(profile_dict, request.text)

        # 3. Select top results
        selected = select_results(results, profile_dict, request.text)

        # 4. Explain results (1 LLM call)
        explained_results, summary_text = explain_results(selected, profile_dict, request.language)

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

        # NEW - compute only from selected schemes:
        # Get required fields from selected schemes only
        needed_facts = set()
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        schemes_path = os.path.join(base_dir, "data", "schemes.json")
        with open(schemes_path, "r", encoding="utf-8") as f:
            all_schemes = json.load(f)
        scheme_map = {s["id"]: s for s in all_schemes}
        
        for r in explained_results:
            if r.scheme_id in scheme_map:
                s = scheme_map[r.scheme_id]
                rules = s.get("rules", {})
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
                # Only add caste_category if scheme explicitly requires it
                if rules.get("categories") and any(cat in ["SC", "ST", "OBC", "EWS"] for cat in rules.get("categories", [])):
                    needed_facts.add("caste_category")

        missing_fields = [f for f in needed_facts if profile_dict.get(f) is None]

        return AnalyzeResponse(
            profile=profile_dict,
            missing_fields=missing_fields,
            results=results_list,
            summary_text=summary_text,
            language=request.language
        )

    except Exception as e:
        logger.exception("Error in /api/analyze")
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            raise HTTPException(status_code=429, detail="The AI is busy, please try again in a minute")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Follow-up chat endpoint. Uses matched scheme IDs from profile for context.
    """
    try:
        # Recompute matched scheme IDs from profile (Python rules only)
        matched_scheme_ids = get_scheme_ids_for_profile(request.profile)

        answer, sources, translation_failed = answer_chat(
            question=request.question,
            profile=request.profile,
            language=request.language,
            history=request.history,
            matched_scheme_ids=matched_scheme_ids
        )

        return ChatResponse(
            answer=answer,
            sources=sources,
            translation_failed=translation_failed
        )

    except Exception as e:
        logger.exception("Error in /api/chat")
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            raise HTTPException(status_code=429, detail="The AI is busy, please try again in a minute")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/explain-pdf", response_model=PdfExplainResponse)
async def explain_pdf_endpoint(file: UploadFile = File(...), language: str = Form(default="en")):
    """
    Explain a PDF document in the target language.
    Rejects files over 10 MB or non-PDF files.
    """
    try:
        # Validate file size (10 MB limit)
        max_size = 10 * 1024 * 1024  # 10 MB
        content = await file.read()
        if len(content) > max_size:
            raise HTTPException(status_code=400, detail="File too large. Maximum size is 10 MB.")

        # Validate PDF content type
        if not file.content_type or not file.content_type.startswith("application/pdf"):
            raise HTTPException(status_code=400, detail="File must be a PDF")

        # Extract text
        text = extract_text(content)

        # Explain PDF
        summary, key_points, who_is_affected, deadlines = explain_pdf(text, language)

        return PdfExplainResponse(
            summary=summary,
            key_points=key_points,
            who_is_affected=who_is_affected,
            deadlines=deadlines,
            language=language
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in /api/explain-pdf")
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            raise HTTPException(status_code=429, detail="The AI is busy, please try again in a minute")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/official-source", response_model=OfficialSourceResponse)
async def official_source_endpoint(request: OfficialSourceRequest):
    """
    Fetch the official scheme page and summarize it in the user's language.
    """
    # Find the scheme
    scheme = SCHEME_MAP.get(request.scheme_id)
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")

    official_link = scheme.get("official_link", "")
    if not official_link:
        return OfficialSourceResponse(
            scheme_id=request.scheme_id,
            scheme_name=scheme.get("name", "Unknown"),
            summary="",
            source_url="",
            success=False,
            error="No official link available for this scheme."
        )

    # Fetch the page with timeout
    try:
        response = requests.get(official_link, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (compatible; SchemeSaathi/1.0)"
        })
        response.raise_for_status()
        html_content = response.text
    except requests.exceptions.Timeout:
        return OfficialSourceResponse(
            scheme_id=request.scheme_id,
            scheme_name=scheme.get("name", "Unknown"),
            summary="",
            source_url=official_link,
            success=False,
            error="The official portal took too long to respond. Please try again later or visit the portal directly."
        )
    except requests.exceptions.RequestException as e:
        return OfficialSourceResponse(
            scheme_id=request.scheme_id,
            scheme_name=scheme.get("name", "Unknown"),
            summary="",
            source_url=official_link,
            success=False,
            error=f"Could not fetch the official portal: {str(e)}"
        )

    # Strip HTML tags
    text_content = re.sub(r"<[^>]+>", " ", html_content)
    text_content = re.sub(r"\s+", " ", text_content).strip()
    text_content = text_content[:8000]  # Limit size for LLM

    # Summarize with LLM
    try:
        from backend.llm import call_text
        from backend.explain import LANGUAGE_NAMES

        lang_name = LANGUAGE_NAMES.get(request.language, "English")
        system_prompt = f"""You are a government scheme information assistant.
Summarize the official scheme page content in {lang_name} ({request.language} script).
Focus on: what the scheme offers, who is eligible, how to apply, key benefits.
Use simple words, short sentences. Max 5 sentences.
Keep scheme names in English. Do not add information not in the source."""

        user_prompt = f"""Scheme: {scheme.get('name', '')}
Official URL: {official_link}

Page content (extracted):
{text_content}

Summarize in {lang_name} ({request.language} script):"""

        summary = call_text(system_prompt, user_prompt, max_tokens=400, temperature=0.3)

        return OfficialSourceResponse(
            scheme_id=request.scheme_id,
            scheme_name=scheme.get("name", "Unknown"),
            summary=summary,
            source_url=official_link,
            success=True,
            error=None
        )

    except Exception as e:
        logger.exception("Error summarizing official source")
        return OfficialSourceResponse(
            scheme_id=request.scheme_id,
            scheme_name=scheme.get("name", "Unknown"),
            summary="",
            source_url=official_link,
            success=False,
            error="Failed to generate summary. Please visit the official portal directly."
        )


@app.post("/api/stt")
async def stt_endpoint(audio: UploadFile = File(...), language: str = Form(default="en")):
    """
    Speech-to-text endpoint.
    Accepts multipart form with 'audio' file and optional 'language' field.
    Returns {"text": transcribed_text, "language": language_code}.
    """
    try:
        # Read audio file
        audio_bytes = await audio.read()

        # Friendly error for empty audio
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file provided")

        # Transcribe
        text = transcribe(audio_bytes, language)

        return {"text": text, "language": language}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error in /api/stt")
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            raise HTTPException(status_code=429, detail="The AI is busy, please try again in a minute")
        raise HTTPException(status_code=500, detail=str(e))


from fastapi import Response

@app.post("/api/tts")
async def tts_endpoint(request: dict):
    """
    Text-to-speech endpoint.
    Accepts JSON with 'text' and 'language' fields.
    Returns audio/mpeg bytes or error JSON.
    """
    text = request.get("text", "")
    language = request.get("language", "en")

    # Validate input
    if not text or not text.strip():
        logger.warning("TTS request with empty text")
        raise HTTPException(status_code=400, detail="Empty text provided")

    # Log the request (truncated for privacy)
    logger.info(f"TTS request: language={language}, text_length={len(text)}, text_preview={text[:100]!r}")

    try:
        # Synthesize
        audio_bytes = synthesize(text, language)

        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=speech.mp3"}
        )

    except ValueError as e:
        logger.warning(f"TTS validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        logger.warning(f"TTS runtime error: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception(f"TTS unexpected error for text={text[:100]!r}, language={language}")
        raise HTTPException(status_code=503, detail="Audio is unavailable right now")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)