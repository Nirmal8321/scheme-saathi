# Prompts for AI Coding Agents

Use with Claude Code / Cursor / Copilot / any coding AI.
Put `design.md` and `progress.md` in the project root first.
Run prompts IN ORDER. Paste one at a time. Check result before next.

---

## PROMPT S1: Project setup (one person does, then push to Git, both pull)

```
You are building a hackathon project called Scheme Saathi.
Read design.md fully. It is the source of truth.

Task S1: create the project skeleton exactly as in design.md Section 4.
- Create all folders and empty placeholder files with a one-line docstring.
- Write requirements.txt: fastapi, uvicorn, python-multipart, pydantic, python-dotenv, anthropic, chromadb, sentence-transformers, pymupdf, faster-whisper, gTTS, streamlit, requests, pytest.
- Write .env.example from design.md Section 10.
- Write README.md with setup + run steps from design.md Section 11.
- Add .gitignore (venv, .env, __pycache__, chroma db folder).
- Do NOT write real logic yet.
When done, mark S1 in progress.md as [x] with one short line.
```

---

# PERSON A PROMPTS (Backend + AI)

## PROMPT A1: Contract first

```
Read design.md. You are Person A (Backend + AI).

Task A1:
1. Write backend/schemas.py with Pydantic models matching design.md Section 6 exactly:
   Profile, SchemeResult, AnalyzeRequest, AnalyzeResponse, ChatRequest, ChatResponse, PdfExplainResponse, SttResponse, TtsRequest.
2. Write backend/mock_data.py with realistic mock responses in Marathi, Hindi, and English for /analyze (3 schemes: PM-KISAN yes, Namo Shetkari yes, Mudra Loan maybe), /chat, and /explain-pdf.
3. Write backend/config.py loading .env (ANTHROPIC_API_KEY, LLM_MODEL, USE_MOCK, etc.).
4. Write backend/main.py with FastAPI, CORS enabled, and routes /api/health, /api/analyze, /api/chat, /api/explain-pdf returning mock data when USE_MOCK=true. Leave /api/stt and /api/tts as stubs that Person B will fill.
5. Make sure `uvicorn backend.main:app` runs and /docs shows all routes.
Update progress.md for A1 with one line. Tell me when to push so Person B can start.
```

## PROMPT A2: Scheme data

```
Read design.md Section 7. Task A2.

Create data/schemes.json with 10 schemes listed in design.md.
- Use only facts from official government sources (pmkisan.gov.in, myscheme.gov.in, maharashtra.gov.in, etc). If you can browse the web, fetch them. If you cannot, write your best knowledge and set "last_verified": "UNVERIFIED" so a human checks it.
- Follow the schema exactly. Fill raw_text with 150-300 words of official-style description per scheme.
- Also create tests/sample_inputs.json with 5 sample user descriptions (farmer in Wardha, woman entrepreneur, student SC category, street vendor, elderly widow) in mixed Marathi/Hindi/English, each with expected eligible scheme ids.
Update progress.md A2 with one line. List which schemes are UNVERIFIED so I can check them.
```

## PROMPT A3: RAG

```
Read design.md. Task A3.

Write backend/rag.py and backend/build_index.py:
- build_index.py: read data/schemes.json, chunk each scheme (one chunk for summary fields, plus chunks of raw_text ~200 words), embed with sentence-transformers paraphrase-multilingual-MiniLM-L12-v2, store in persistent ChromaDB at ./chroma_db with metadata scheme_id.
- rag.py: function search(query: str, k: int = 6) -> list of {scheme_id, text, score}; also get_scheme(scheme_id) and list_schemes().
- Search must work for Marathi/Hindi/English queries.
- Add a quick test script that searches "farmer 2 acre income support" and prints results.
Update progress.md A3 with one line.
```

## PROMPT A4: Profile extractor

```
Read design.md Section 8. Task A4.

Write backend/llm.py: small wrapper around the Anthropic client with function call_json(system, user, max_tokens) that returns parsed JSON, strips code fences, and retries once on bad JSON. Model from config.

Write backend/extract.py: extract_profile(text: str) -> (Profile, missing_fields). Use the LLM #1 prompt spec. Input can be Marathi, Hindi, English or mixed. Never guess; use null. Convert income words ("80 hajar", "ek lakh") to a number in INR per year.

Test with tests/sample_inputs.json and print results.
Update progress.md A4 with one line.
```

## PROMPT A5: Eligibility matcher

```
Read design.md Section 8. Task A5.

Write backend/match.py: match_schemes(profile, query_text) -> list[SchemeResult-without-explanation].
- Use rag.search to get top chunks (k=8), group by scheme_id.
- Call LLM #2 with the profile + scheme context. Use ONLY the context. Unknown rule => "maybe". Include source_quote copied from context, and carry documents, how_to_apply, official_link, benefit from schemes.json.
- Return at most 5 schemes, sorted: yes, maybe, no.
Test on the 5 sample users, print a table of scheme vs eligible.
Update progress.md A5 with one line.
```

## PROMPT A6: Explainer + chat

```
Read design.md Section 8. Task A6.

Write backend/explain.py:
- explain_results(results, profile, language) -> (results with 'explanation' filled, summary_text). Write in target language script, 6th-grade words, short sentences, benefit first. Keep summary_text under 80 words so it is good for voice.
- answer_chat(question, profile, language, history) -> (answer, sources). Retrieve context with rag.search. If answer is not in context, say not sure and point to official link.
Write backend/pdf_reader.py: extract_text(pdf_bytes) using PyMuPDF.
Add explain_pdf(text, language) -> summary, key_points, who_is_affected, deadlines.
Test with Marathi and Hindi.
Update progress.md A6 with one line.
```

## PROMPT A7: Real routes

```
Read design.md Section 6. Task A7.

In backend/main.py wire real logic (keep USE_MOCK switch working):
- /api/analyze: extract_profile (merge profile_override) -> match_schemes -> explain_results -> AnalyzeResponse with disclaimer.
- /api/chat, /api/explain-pdf as per contract.
- Friendly JSON errors {"error": "..."} and logging. Timeout safe.
Test with curl for each route and show me the outputs.
Update progress.md A7 with one line.
```

## PROMPT A8: Tests

```
Task A8. Write tests/test_api.py with pytest: run the 5 sample users through /api/analyze with USE_MOCK=false and check response shape matches schema and expected scheme ids appear as yes/maybe. Print a summary of failures. Fix prompt bugs in extract/match if tests fail.
Update progress.md A8 with one line.
```

---

# PERSON B PROMPTS (Voice + UI + Demo)

## PROMPT B1: UI skeleton (works on mock)

```
Read design.md Sections 6 and 12. You are Person B (Voice + UI + Demo).
Pull latest code. Backend runs with USE_MOCK=true.

Task B1:
- Write ui/api_client.py: functions analyze(), chat(), explain_pdf(), stt(), tts() calling BACKEND_URL with requests, timeouts, and friendly error handling.
- Write ui/app.py Streamlit page: language picker, text box, "Find my schemes" button, shows raw JSON for now.
- Make it run with `streamlit run ui/app.py` against the mock backend.
Update progress.md B1 with one line.
```

## PROMPT B2: STT

```
Task B2. Read design.md.

Write backend/stt.py using faster-whisper (small model, cpu, int8). Function transcribe(audio_bytes, language) -> text. Map our language codes (mr, hi, en, ta, bn, te, gu, kn) to whisper codes. Convert webm/wav input safely (use temp file).
Implement POST /api/stt in backend/main.py per contract (only edit the stt route and imports).
In ui/app.py add st.audio_input mic button; send audio to /api/stt; put recognized text in the editable text box.
Test Marathi and Hindi speech. Tell me accuracy honestly.
Update progress.md B2 with one line.
```

## PROMPT B3: TTS

```
Task B3. Read design.md.

Write backend/tts.py using gTTS. Function synthesize(text, language) -> mp3 bytes. Cache by hash(text+language) in ./tts_cache to save time.
Implement POST /api/tts per contract (only edit the tts route).
In UI add a "Play" button that plays returned audio with st.audio.
Test Marathi, Hindi, English. If Marathi sounds bad, tell me.
Update progress.md B3 with one line.
```

## PROMPT B4: Scheme cards

```
Task B4. Read design.md Section 12.

Write ui/components.py and use in ui/app.py:
- Profile summary box.
- Scheme card: colored badge (green Eligible / yellow Maybe / red Not eligible), scheme name, benefit, reason, documents as checklist, how to apply, official link button, source quote in small italic, explanation text, and a "Play audio" button using /api/tts.
- A big "Play full summary" button for summary_text.
- Footer disclaimer.
Clean, large fonts, mobile friendly, simple colors. Show loading spinner during calls.
Update progress.md B4 with one line.
```

## PROMPT B5: Missing info flow

```
Task B5. When response.missing_fields is not empty, show friendly input widgets for each field (age number, caste category dropdown, gender dropdown, etc.) in the selected language labels. On submit, call /api/analyze again with profile_override and refresh results. Keep previous text.
Update progress.md B5 with one line.
```

## PROMPT B6: Follow-up chat

```
Task B6. Add a follow-up chat section under results: text input + mic button. Calls /api/chat with profile, language, history. Show answers as chat bubbles with a play-audio button and sources.
Update progress.md B6 with one line.
```

## PROMPT B7: PDF tab

```
Task B7. Add a second tab "Understand a notification (PDF)": file uploader, language, button. Calls /api/explain-pdf. Show summary, key points, who is affected, deadlines, plus Play-audio button.
Update progress.md B7 with one line.
```

## PROMPT B8: Polish

```
Task B8. Polish UI: app title and tagline, sample-input buttons ("Try: Farmer in Wardha", "Try: Woman entrepreneur") that fill the text box, clear error messages if backend or API fails, a "Demo mode" toggle that uses cached sample outputs, consistent spacing. Remove debug JSON.
Update progress.md B8 with one line.
```

---

# INTEGRATION PROMPTS (both)

## PROMPT I1: End to end check

```
Both Person A and B code is merged. Run backend with USE_MOCK=false and UI. Test these flows end to end and fix bugs:
1. Marathi voice -> profile -> schemes -> audio.
2. Hindi text -> missing-info question -> refreshed results.
3. Follow-up question by voice.
4. PDF upload.
Report a bug list, fix them, rerun. Update progress.md I1 with one line.
```

## PROMPT I2: Demo safety

```
Create demo_cache/ with saved JSON and mp3 outputs for 3 demo inputs (Marathi farmer, Hindi woman entrepreneur, English student). Add a DEMO_OFFLINE=true switch so the UI plays these if the internet or API fails. Write DEMO.md with the exact 3-minute script from design.md Section 14 and the exact phrases to speak.
Update progress.md I2/I3 notes with one line.
```
