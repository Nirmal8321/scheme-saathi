# Scheme Saathi

Voice-first app. Citizen speaks in own language, says who they are. App finds govt schemes they qualify for, explains in voice, lists documents and how to apply.

**Knowledge base curated from official sources (link per scheme). Analysis, translation, voice and PDF reading are live.**

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