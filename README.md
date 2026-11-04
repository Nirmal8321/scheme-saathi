# Scheme Saathi

Voice-first assistant that helps Indian citizens find the government schemes they qualify for. A user speaks or types about themselves in Marathi, Hindi or English. The app returns matching schemes with the benefit, documents needed, how to apply, and a simple explanation in their language, with audio.

Built for the hackathon theme **Civic Pulse, Digital Governance and Public Information** (problem: Multilingual Policy, Rights and Scheme Explainer).

## The main idea

**Python rules decide eligibility. The AI only understands and explains.**

- The AI turns the user's words into a structured profile (age, income, state, job). Unknown facts stay empty. It never guesses.
- A deterministic rule engine checks the profile against each scheme and returns **yes**, **maybe** or **no**.
- Missing facts make a scheme **maybe**, and the app asks one clear follow-up question.
- Benefits, documents and links are copied from the scheme data, not written by the AI.
- Every scheme has an official source link.

## How it works

```
Voice -> Speech-to-Text -> AI profile extractor -> Python rule engine
      -> Search over scheme data (RAG) -> AI explainer -> Text-to-Speech -> Screen
```

1. The user speaks or types.
2. The profile extractor (LLM) fills a structured profile, and Python checks it.
3. The rule engine compares the profile with every scheme.
4. The best matches are selected and ranked.
5. The explainer writes simple text in the chosen language. Python adds the facts and the follow-up question.
6. Text-to-speech reads the answer aloud.

## Features

- Marathi, Hindi and English input and output
- Voice input (speech-to-text) and voice output (text-to-speech)
- Eligible, Maybe and Not eligible results with reasons
- One follow-up question when a key fact is missing
- Source quote and official link for each scheme
- "Check official source": fetches the official page live and summarizes it
- Backend routes for follow-up chat and for explaining a government PDF notice

## Tech stack

| Part | Tool |
|---|---|
| Screen | Streamlit |
| AI model | Google Gemini (Flash model, set in `.env` / Streamlit Secrets) |
| Speech to text | Gemini Audio Transcription |
| Text to speech | gTTS |
| Search | Gemini Embeddings + NumPy Cosine Similarity |
| PDF reading | PyMuPDF |
| Rule engine | Pure Python (backend/rules.py) |

## Setup (Local)

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
python -m backend.build_index  # builds the search index (first time only)
```

## Configuration

Copy `.env.example` to `.env` and fill in the values:

```bash
copy .env.example .env         # Windows
```

```
LLM_PROVIDER=google
LLM_API_KEY=your_key_here
LLM_MODEL=gemini-2.5-flash
STT_MODEL=gemini-2.5-flash
TTS_PROVIDER=gtts
```

Never commit `.env`. It is listed in `.gitignore`.

**For Streamlit Community Cloud:** Add the same keys in **Settings → Secrets** instead of `.env`:
```toml
LLM_PROVIDER = "google"
LLM_API_KEY = "your_key_here"
LLM_MODEL = "gemini-2.5-flash"
STT_MODEL = "gemini-2.5-flash"
TTS_PROVIDER = "gtts"
```

## Run (Single Process - Streamlit Community Cloud)

```bash
streamlit run ui/app.py
```

The app starts the AI engine automatically on first load (builds index if needed, ~30s on first run).

## Run (Local Development - Two Processes)

Terminal 1, backend (optional, for API testing):
```bash
pip install -r requirements-dev.txt
uvicorn backend.main:app --port 8000
```

Terminal 2, frontend:
```bash
streamlit run ui/app.py
```

Open `http://localhost:8501`. The backend test page is at `http://localhost:8000/docs`.

## Tests

```bash
python tests/test_rules.py       # rule engine (no AI call)
python tests/test_select.py      # selection and ranking (no AI call)
python tests/test_currency.py    # money text in Hindi and Marathi (no AI call)
python tests/test_rag.py         # search
python tests/test_match.py       # sample users vs expected results
```

Some tests call the AI and use free-tier quota, so run them sparingly.

## Project structure

```
scheme-saathi/
├── data/
│   ├── schemes.json     # scheme knowledge base (13 schemes, source link per scheme)
│   └── index.npz        # pre-computed Gemini embeddings (committed)
├── backend/              # AI calls, rule engine, search, voice, PDF
├── ui/                   # Streamlit frontend
└── tests/                # test scripts and sample users
```

## Data note

The scheme data is curated from official government sources into `data/schemes.json`, with a source link and a last-verified date per scheme. It is a knowledge base, not a live government API. Scheme rules and amounts change over time, so re-verify before relying on them.

The search index `data/index.npz` contains pre-computed Gemini embeddings for all scheme chunks. It is built with `python -m backend.build_index` and committed to the repo.

## Known limitations

- Covers 13 schemes, with simplified rules.
- Gemini audio transcription may have occasional errors.
- The free AI quota is small, so heavy use can show "the AI is busy".
- Guidance only. Always verify on the official portal before applying.

## Deployment: Streamlit Community Cloud

1. Fork this repo
2. Go to https://share.streamlit.io/
3. New app → select repo/branch
4. Main file: `ui/app.py`
5. Add secrets in **Settings → Secrets** (see Configuration above)
6. Deploy

Requirements: ~400 MB RAM (well under 1 GB limit). Single Streamlit process, no separate backend.

## Roadmap

See `FUTURE_FEATURES.md`: a larger scheme database with paging and filters, a richer profile format, a WhatsApp or Telegram bot, and permanent cloud hosting.