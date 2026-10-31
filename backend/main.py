"""FastAPI app entry point with routes for analyze, chat, explain-pdf, health, stt, tts."""
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, RedirectResponse
from backend.config import USE_MOCK
from backend.schemas import (
    AnalyzeRequest, AnalyzeResponse,
    ChatRequest, ChatResponse,
    PdfExplainResponse,
    SttResponse, TtsRequest,
    HealthResponse, ErrorResponse
)

# Import mock data only when needed
if USE_MOCK:
    from backend.mock_data import (
        get_mock_analyze_response,
        get_mock_chat_response,
        get_mock_pdf_explain_response
    )

app = FastAPI(
    title="Scheme Saathi API",
    description="Voice-first government scheme eligibility checker",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint - redirects to API documentation."""
    return RedirectResponse(url="/docs")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Favicon endpoint - returns 204 No Content to avoid 404."""
    return Response(status_code=204)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler - returns friendly error messages."""
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error. Please try again."}
    )


@app.get("/api/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse(status="ok", mock=USE_MOCK)


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    """
    Main flow: text in, full eligibility result out.
    Returns mock data when USE_MOCK=true.
    """
    try:
        if USE_MOCK:
            return get_mock_analyze_response(request.language)

        # TODO: Implement real analysis pipeline
        # 1. Extract profile using LLM #1
        # 2. Search schemes via RAG
        # 3. Match eligibility using LLM #2
        # 4. Generate explanations using LLM #3
        raise HTTPException(status_code=501, detail="Real backend not implemented yet")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Follow-up question about the results.
    Returns mock data when USE_MOCK=true.
    """
    try:
        if USE_MOCK:
            return get_mock_chat_response(request.question, request.language)

        # TODO: Implement real chat with LLM #3
        raise HTTPException(status_code=501, detail="Real backend not implemented yet")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@app.post("/api/explain-pdf", response_model=PdfExplainResponse)
async def explain_pdf(file: UploadFile = File(...), language: str = Form(...)):
    """
    Explain uploaded PDF in plain language.
    Returns mock data when USE_MOCK=true.
    """
    try:
        if not file.filename.endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")

        if USE_MOCK:
            # Read and discard the file content for mock
            await file.read()
            return get_mock_pdf_explain_response(language)

        # TODO: Implement real PDF extraction and explanation
        # 1. Extract text using PyMuPDF
        # 2. Summarize using LLM
        raise HTTPException(status_code=501, detail="Real backend not implemented yet")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF explanation failed: {str(e)}")


@app.post("/api/stt", response_model=SttResponse)
async def stt(file: UploadFile = File(...), language: str = Form(...)):
    """
    Speech to text endpoint.
    Returns 501 stub for now.
    """
    raise HTTPException(status_code=501, detail="STT not implemented yet")


@app.post("/api/tts")
async def tts(request: TtsRequest):
    """
    Text to speech endpoint.
    Returns 501 stub for now.
    """
    raise HTTPException(status_code=501, detail="TTS not implemented yet")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)