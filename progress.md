B1: Implemented UI api_client.py (analyze, chat, explain_pdf, stt, tts with timeouts & error handling)
B2: Implemented STT with faster-whisper (transcribe function, /api/stt endpoint, test script)
B3: Implemented TTS with gTTS (synthesize function, caching, text cleaning, /api/tts endpoint, test script)
B4: Implemented Streamlit UI (app.py, components.py, mic input, sample buttons, scheme cards, TTS playback)
B1 fix: TTS robust (empty text 400, 1500 char limit, URL/markdown/emoji/₹ strip, 503 on gTTS fail, UI shows friendly error)
B2 fix: Badge mapping fixed (yes=green Eligible, maybe=yellow Maybe: needs a check, no=red Not eligible), requires_verification returns maybe
B3 fix: Money post-processing fixed for hi/mr (5 lakh rupees -> 5 लाख रुपये, Rs 2.67 lakh -> 2.67 लाख रुपये, Rs 6,000 -> 6,000 रुपये), unit tests added
B4 fix: Added PMFBY, KCC, Maharashtra seed_subsidy schemes with full rules; category-based ranking in select_results (insurance/seeds/loan/scholarship/house/gas/health keywords); no-LLM test verifies pmfby in top 3 for "farmer crop insurance seeds"
Demo: Created demo_cache/ with 3 cached profiles (Marathi farmer, Hindi widow, English student) + JSON responses + MP3 audio; DEMO_OFFLINE=true in .env; sidebar demo buttons; DEMO.md with 3-min script & exact phrases