---
sdk: docker
app_port: 7860
---

# Scheme Saathi

Voice-first app. Citizen speaks in own language, says who they are. App finds govt schemes they qualify for, explains in voice, lists documents and how to apply.

**Knowledge base curated from official sources (link per scheme). Analysis, translation, voice and PDF reading are live.**

## Hugging Face Space Deployment

This project is configured to run as a Hugging Face Space using Docker SDK.

### Quick Deploy to HF Spaces

1. **Create a new Space** on [huggingface.co/new-space](https://huggingface.co/new-space)
   - Owner: your username/organization
   - Space name: `scheme-saathi` (or your choice)
   - License: Apache-2.0 (or your choice)
   - SDK: **Docker**
   - App port: **7860** (auto-detected from Dockerfile)

2. **Push this repository** to the Space:
   ```bash
   git clone https://huggingface.co/spaces/YOUR_USERNAME/scheme-saathi
   cd scheme-saathi
   # Copy all project files here
   git add .
   git commit -m "Initial commit"
   git push
   ```

3. **Set Secrets** in Space Settings → Repository secrets:
   - `LLM_API_KEY` — Your LLM API key (Anthropic, Google, etc.)
   - `LLM_PROVIDER` — `anthropic` or `google`
   - `LLM_MODEL` — e.g., `claude-sonnet-5-5` or `gemini-3.5-flash-lite`

   Optional overrides:
   - `STT_MODEL` — `base` (default), `small`, `medium`
   - `TTS_PROVIDER` — `gtts` (default)
   - `DEMO_OFFLINE` — `false` (default)

4. **Build & Run** — HF Spaces will automatically build the Docker image and deploy. First build takes ~3-5 minutes (pre-downloads models). Subsequent builds are faster with layer caching.

### Local Development with Docker

```bash
# Build
docker build -t scheme-saathi .

# Run (requires .env file with API keys)
docker run -p 7860:7860 --env-file .env scheme-saathi
```

## Setup

```bash
pip install -r requirements.txt
python -m backend.build_index        # build Chroma index
```

## Run

```bash
# Terminal 1 - Backend
uvicorn backend.main:app --reload --port 8000

# Terminal 2 - Frontend
streamlit run ui/app.py
```

## Configuration

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY
```

## Project Structure

```
scheme-saathi/
├── data/              # Scheme data and PDFs
├── backend/           # FastAPI + AI logic
├── ui/                # Streamlit frontend
└── tests/             # Test cases
```

## Environment Variables

See `.env.example` for all options.

---

*Knowledge base curated from official sources (link per scheme). Analysis, translation, voice and PDF reading are live.*