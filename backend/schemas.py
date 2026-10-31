"""Pydantic models defining the API contract between frontend and backend."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class Profile(BaseModel):
    """Extracted user profile from free text input."""
    occupation: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    annual_income: Optional[int] = None
    income_note: Optional[str] = None
    land_acres: Optional[float] = None
    caste_category: Optional[str] = None
    family_members: Optional[int] = None


class SchemeResult(BaseModel):
    """Single scheme eligibility result."""
    scheme_id: str
    scheme: str
    eligible: str = Field(..., pattern="^(yes|no|maybe)$")
    reason: str
    benefit: str
    documents: List[str]
    how_to_apply: str
    official_link: str
    source_quote: str
    explanation: str


class AnalyzeRequest(BaseModel):
    """Request for /api/analyze endpoint."""
    text: str
    language: str = Field(..., pattern="^(en|hi|mr|ta|bn|te|gu|kn)$")
    profile_override: Optional[Dict[str, Any]] = None


class AnalyzeResponse(BaseModel):
    """Response for /api/analyze endpoint."""
    profile: Profile
    missing_fields: List[str]
    results: List[SchemeResult]
    summary_text: str
    language: str
    disclaimer: str = "Verify at official portal before applying."


class ChatRequest(BaseModel):
    """Request for /api/chat endpoint."""
    question: str
    profile: Dict[str, Any]
    language: str = Field(..., pattern="^(en|hi|mr|ta|bn|te|gu|kn)$")
    history: List[Dict[str, str]] = []


class ChatResponse(BaseModel):
    """Response for /api/chat endpoint."""
    answer: str
    sources: List[str]


class PdfExplainResponse(BaseModel):
    """Response for /api/explain-pdf endpoint."""
    summary: str
    key_points: List[str]
    who_is_affected: str
    deadlines: List[str]
    language: str


class SttResponse(BaseModel):
    """Response for /api/stt endpoint."""
    text: str
    language: str


class TtsRequest(BaseModel):
    """Request for /api/tts endpoint."""
    text: str
    language: str = Field(..., pattern="^(en|hi|mr|ta|bn|te|gu|kn)$")


class HealthResponse(BaseModel):
    """Response for /api/health endpoint."""
    status: str
    mock: bool


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str