# Scheme Saathi: Software Design

Voice-first app. Citizen speaks in own language, says who they are. App finds govt schemes they qualify for, explains in voice, lists documents and how to apply.

Hackathon track: Civic Pulse, Digital Governance & Public Information
Problem: Multilingual Policy, Rights & Scheme Explainer

---

## 1. Goals

- Voice/text/PDF in, plain-language explainer (text + voice) in regional language out.
- Personal eligibility match: Eligible / Maybe / Not eligible, with reason and source quote.
- Ask for missing info instead of guessing.
- Works in 24 hrs. No hardware. Use existing LLM API (no model training).

Non-goals: login, database of users, payments, real application submission.

---

## 2. Architecture

```
User (voice / text / PDF)
        |
        v
  [Streamlit UI]  <---- Person B
        |  HTTP (JSON)
        v
  [FastAPI backend] <---- Person A
        |
        +--> STT  (voice -> text)             [Person B module]
        +--> LLM #1 Profile Extractor         [Person A]
        +--> RAG search (Chroma, schemes)     [Person A]
        +--> LLM #2 Eligibility Matcher       [Person A]
        +--> LLM #3 Explainer (target lang)   [Person A]
        +--> TTS  (text -> mp3)               [Person B module]
```

---

## 3. Tech Stack

| Part | Choice |
|---|---|
| Language | Python 3.11 |
| LLM | Claude API (model name in env `LLM_MODEL`) |
| Embeddings | sentence-transformers `paraphrase-multilingual-MiniLM-L12-v2` |
| Vector DB | ChromaDB (local, persistent) |
| PDF | PyMuPDF (`fitz`) |
| Backend | FastAPI + Uvicorn |
| Frontend | Streamlit (use `st.audio_input` for mic) |
| STT | `faster-whisper` small model (default); Bhashini optional |
| TTS | `gTTS` (default, no key; supports hi, mr, ta, bn, te, gu, kn, en) |
| Config | `python-dotenv` |

---

## 4. Repo Structure

```
scheme-saathi/
├── design.md
├── progress.md
├── prompts.md
├── README.md
├── requirements.txt
├── .env.example
├── data/
│   ├── schemes.json          # structured scheme data (Person A)
│   └── pdfs/                 # optional raw PDFs
├── backend/
│   ├── main.py               # FastAPI app, routes (A)
│   ├── config.py             # env + constants (A)
│   ├── schemas.py            # Pydantic models = API contract (A)
│   ├── llm.py                # Claude client wrapper (A)
│   ├── extract.py            # LLM #1 profile extractor (A)
│   ├── rag.py                # Chroma index + search (A)
│   ├── match.py              # LLM #2 eligibility matcher (A)
│   ├── explain.py            # LLM #3 explainer + chat (A)
│   ├── pdf_reader.py         # PDF -> text (A)
│   ├── stt.py                # speech to text (B)
│   ├── tts.py                # text to speech (B)
│   └── mock_data.py          # mock responses so B can start early (A)
├── ui/
│   ├── app.py                # Streamlit main (B)
│   ├── api_client.py         # calls backend, with mock fallback (B)
│   └── components.py         # scheme card, badges, audio player (B)
└── tests/
    ├── sample_inputs.json    # 5 sample users (A)
    └── test_api.py           # (A)
```

---

## 5. Work Split

### Person A: Backend + AI brain
Owns: data, RAG, all LLM prompts, FastAPI routes, schemas, mock data.

### Person B: Voice + UI + Demo
Owns: STT, TTS, Streamlit UI, PDF upload UI, language picker, demo script, pitch.

### Shared contract
`backend/schemas.py` and Section 6 below are the contract. **Do not change the contract without telling the other person.** A ships `mock_data.py` and mock mode early (`USE_MOCK=true`) so B can build UI with no real backend.

---

## 6. API Contract

Base URL: `http://localhost:8000`

### GET `/api/health`
Response: `{"status":"ok","mock":false}`

### POST `/api/analyze`
Main flow. Text in, full result out.

Request:
```json
{
  "text": "Mi shetkari aahe, Wardha madhe. 2 acre jamin. Varshik utpanna 80000.",
  "language": "mr",
  "profile_override": null
}
```
`language`: one of `en, hi, mr, ta, bn, te, gu, kn`.
`profile_override`: optional dict to merge when user answers a missing-info question.

Response:
```json
{
  "profile": {
    "occupation": "farmer",
    "age": null,
    "gender": null,
    "state": "Maharashtra",
    "district": "Wardha",
    "annual_income": 80000,
    "land_acres": 2,
    "caste_category": null,
    "family_members": null
  },
  "missing_fields": ["age", "caste_category"],
  "results": [
    {
      "scheme_id": "pm_kisan",
      "scheme": "PM-KISAN",
      "eligible": "yes",
      "reason": "Small farmer with land.",
      "benefit": "Rs 6,000 per year in 3 installments",
      "documents": ["Aadhaar", "7/12 land record", "Bank passbook"],
      "how_to_apply": "pmkisan.gov.in or nearest CSC center",
      "official_link": "https://pmkisan.gov.in",
      "source_quote": "short quote from official text",
      "explanation": "Text in the requested language, simple words."
    }
  ],
  "summary_text": "Overall short voice script in requested language.",
  "language": "mr",
  "disclaimer": "Verify at official portal before applying."
}
```
`eligible`: `"yes" | "no" | "maybe"`.

### POST `/api/chat`
Follow-up question about the results.

Request:
```json
{
  "question": "Documents kon-kon lagtil?",
  "profile": { },
  "language": "mr",
  "history": []
}
```
Response:
```json
{ "answer": "text in language", "sources": ["pm_kisan"] }
```

### POST `/api/explain-pdf`
Multipart form: `file` (PDF), `language` (string).

Response:
```json
{
  "summary": "plain language summary in language",
  "key_points": ["..."],
  "who_is_affected": "...",
  "deadlines": ["..."],
  "language": "mr"
}
```

### POST `/api/stt`
Multipart form: `audio` (wav/mp3/webm), `language`.
Response: `{"text": "recognized text", "language": "mr"}`

### POST `/api/tts`
Request: `{"text": "...", "language": "mr"}`
Response: audio bytes, `Content-Type: audio/mpeg`.

### Errors
All errors: HTTP 4xx/5xx with `{"error": "short message"}`. UI must show friendly message, never crash.

---

## 7. Scheme Data Schema (`data/schemes.json`)

List of objects:
```json
{
  "id": "pm_kisan",
  "name": "PM-KISAN",
  "level": "central",
  "state": null,
  "category": "agriculture",
  "benefit": "Rs 6,000 per year in 3 installments",
  "eligibility": [
    "Landholding farmer family",
    "Excludes income tax payers and institutional landholders"
  ],
  "documents": ["Aadhaar", "Land record", "Bank passbook"],
  "how_to_apply": "Register at pmkisan.gov.in or via CSC center",
  "official_link": "https://pmkisan.gov.in",
  "last_verified": "2026-10-31",
  "raw_text": "Longer official text used for RAG."
}
```

Target 10 schemes: PM-KISAN, Namo Shetkari Mahasanman Nidhi, Ladki Bahin (Maharashtra), Mudra Loan, PM Ujjwala, Ayushman Bharat PM-JAY, PM Awas Yojana, PM SVANidhi, Stand-Up India, Post-matric scholarship.

**Data must come from official pages. A human must verify each scheme before the demo.**

---

## 8. LLM Prompts (spec)

All prompts live in the module that uses them. Always request JSON only, parse safely, retry once on bad JSON.

**LLM #1 Profile Extractor** (`extract.py`)
- Input: user text (any Indian language or Hinglish).
- Output JSON: occupation, age, gender, state, district, annual_income (number, INR/year), land_acres, caste_category, family_members, missing_fields.
- Rule: null if not said. Never guess.

**LLM #2 Eligibility Matcher** (`match.py`)
- Input: profile + top-k scheme chunks from RAG.
- Output: list of result objects (see contract, without `explanation`).
- Rule: use ONLY provided context. If rule unknown, answer `maybe`. Always include a short `source_quote` copied from context.

**LLM #3 Explainer** (`explain.py`)
- Input: matcher results + target language.
- Output: `explanation` per scheme and `summary_text`.
- Rule: 6th-grade words, short sentences, benefit first, no jargon, write in target language script.

**Chat** (`explain.py`)
- Answer follow-ups using profile + retrieved scheme context. If not in context, say "not sure, check official site".

---

## 9. Languages

Priority: `mr` (Marathi), `hi` (Hindi), `en`. Then `ta, bn, te, gu, kn` if time.
Test Marathi voice early. If bad, demo in Hindi.

---

## 10. Config (`.env`)

```
ANTHROPIC_API_KEY=
LLM_MODEL=claude-sonnet-5-5
USE_MOCK=false
BACKEND_URL=http://localhost:8000
STT_PROVIDER=faster_whisper
TTS_PROVIDER=gtts
```

---

## 11. Run

```
pip install -r requirements.txt
python -m backend.build_index        # build Chroma index (A)
uvicorn backend.main:app --reload --port 8000
streamlit run ui/app.py
```

---

## 12. UI Spec (Person B)

Single page, big buttons, mobile friendly.
1. Language picker (top).
2. Mic button (record) + text box + "Upload PDF" tab.
3. Show recognized text so user can edit.
4. "Find my schemes" button.
5. Profile summary box.
6. Scheme cards: badge (green Eligible / yellow Maybe / red Not eligible), benefit, documents, how to apply, official link, source quote, play-audio button.
7. If `missing_fields` not empty: show friendly question inputs, resubmit with `profile_override`.
8. Follow-up chat box (voice or text).
9. Footer: disclaimer.

---

## 13. Risks

| Risk | Fix |
|---|---|
| LLM hallucinates rules | RAG only, source quote, `maybe` option |
| Marathi STT/TTS weak | Test hr 8; fall back to Hindi |
| API down at demo | `USE_MOCK=true` + recorded backup video |
| Outdated scheme rules | `last_verified` date + official link |

---

## 14. Demo Script (3 min)

1. Show 60-page legal PDF. Say the problem.
2. Speak Marathi: farmer profile.
3. Show profile + 3 scheme cards + badges.
4. Play Marathi audio.
5. Ask follow-up by voice: "Documents kon-kon lagtil?"
6. Upload a govt notification PDF, show plain summary.
7. Close: "60-page legal PDF to 30-second voice in your own language."

---

## 15. Rules for AI Coding Agents

- Read `design.md` first. Follow the contract exactly.
- Only touch files owned by your person unless told otherwise.
- Keep code simple, typed, commented briefly. No over-engineering.
- Never hardcode API keys. Use `.env`.
- After finishing each task, add ONE line to `progress.md` (mark `[x]` and short note).
- If something in the contract must change, stop and tell the human.
