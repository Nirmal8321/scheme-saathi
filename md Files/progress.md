# Progress

Rule: when a task is done, change `[ ]` to `[x]` and add ONE short line after it. No details.

## Shared

- [x] S1 Repo skeleton, requirements.txt, .env.example, README created

## Person A: Backend + AI

- [x] A1 schemas.py and mock_data.py created (contract matches design.md)
- [x] A2 schemes.json built with 10 real schemes
- [x] A3 RAG index built and search works
- [x] A4 Profile extractor (LLM #1) works — added Python post-processing: gender override, income daily-marker nulling with note, sanity guard <1000, occupation fallback, missing_fields from nulls
- [x] A5 Eligibility matcher (LLM #2) works — check_rules with requires_verification, mudra occupations fixed, all 50 tests pass
- [ ] A6 Explainer in target language (LLM #3) works
- [ ] A7 FastAPI routes /analyze /chat /explain-pdf /health work
- [x] A8 Tests with 5 sample users pass

## Person B: Voice + UI + Demo

- [ ] B1 Streamlit UI skeleton runs with mock data
- [ ] B2 STT module (stt.py) and /api/stt route work
- [ ] B3 TTS module (tts.py) and /api/tts route work
- [ ] B4 Scheme cards, badges, audio player done
- [ ] B5 Missing-info questions flow done
- [ ] B6 Follow-up chat (voice + text) done
- [ ] B7 PDF upload explainer tab done
- [ ] B8 UI polish, error messages, disclaimer done

## Integration + Demo

- [ ] I1 UI connected to real backend end to end
- [ ] I2 Marathi and Hindi tested end to end
- [ ] I3 Backup demo video recorded
- [ ] I4 Slides and pitch ready
