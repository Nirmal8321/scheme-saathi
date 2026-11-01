# Scheme Saathi — 3-Minute Demo Script

## Setup (30 seconds before demo)

```bash
# Terminal 1: Backend (mock mode)
cd scheme-saathi
$env:USE_MOCK="true"; python -m backend.main

# Terminal 2: UI (demo offline mode)
cd scheme-saathi
$env:DEMO_OFFLINE="true"; streamlit run ui/app.py
```

Open browser at `http://localhost:8501`. Sidebar shows **🎬 Demo Mode** with 3 buttons.

---

## Demo Flow (3 minutes total)

### 0:00–0:30 — Marathi Farmer (Wardha) 🌾

**Click sidebar:** `🌾 Marathi Farmer (Wardha)`

**Speak this exact phrase into mic (or click the button):**
> "मी ४२ वर्षाचा शेतकरी आहे, वर्धा, महाराष्ट्रातून. माझी वार्षिक उत्पन्न १.२ लाख रुपये आहे आणि माझ्याकडे ३ एकर जमीन आहे. मी कापूस आणि सोयाबीन पीक घेतो. मला पीक विमा आणि बीज योजनेची माहिती हवी आहे."

**Click:** `🔍 Find My Schemes`

**Show results instantly appear (cached):**
- ✅ PM-KISAN — ₹6,000/year
- ✅ PMFBY — Crop insurance
- ✅ Seed Subsidy — 50% on certified seeds
- ✅ KCC — ₹3 lakh revolving credit
- ✅ Namo Shetkari — Additional ₹6,000/year

**Click:** `🔊 Play Audio` on PMFBY card → **Hear Marathi audio**

**Click:** `🔊 Play Full Summary` → **Hear full Marathi summary**

**Say:** *"All 5 schemes loaded in <1 second from cache. Marathi audio plays offline."*

---

### 0:30–1:30 — Hindi Elderly Widow 👵

**Click sidebar:** `👵 Hindi Elderly Widow`

**Speak this exact phrase into mic (or click the button):**
> "मैं ६८ वर्ष की विधवा महिला हूँ, चेन्नई, तमिलनाडु से। मेरी कोई नियमित आय नहीं है और मैं अपनी बेटी के साथ रहती हूँ। मुझे पेंशन और स्वास्थ्य सहायता की आवश्यकता है।"

**Click:** `🔍 Find My Schemes`

**Show results:**
- ⚠️ PM Ujjwala — Free LPG (needs BPL verification)
- ⚠️ PM-JAY — ₹5 lakh health cover (needs SECC verification)
- ⚠️ PM Awas — Housing subsidy (needs house ownership check)

**Click:** `🔊 Play Full Summary` → **Hear Hindi audio**

**Say:** *"Elderly widow profile — all 'maybe' because verifications needed. Hindi audio works offline."*

---

### 1:30–2:30 — English Student 🎓

**Click sidebar:** `🎓 English Student`

**Speak this exact phrase into mic (or click the button):**
> "I am a 22-year-old student from Delhi. My family income is 3 lakh per year. I am pursuing a postgraduate degree and need scholarship information for SC category students."

**Click:** `🔍 Find My Schemes`

**Show results:**
- ✅ Post-Matric Scholarship — Maintenance + tuition + books
- ❌ Mudra Loan — Not for students

**Click:** `🔊 Play Full Summary` → **Hear English audio**

**Say:** *"Student profile — scholarship approved instantly. English audio works offline."*

---

### 2:30–3:00 — Key Points & Wrap Up

| Feature | Demo Proof |
|---------|------------|
| **Multilingual** | Marathi / Hindi / English audio |
| **Offline-first** | Cached JSON + MP3 load in <100ms |
| **Graceful fallback** | `DEMO_OFFLINE=true` bypasses API/internet |
| **Category boost** | Insurance/seeds keywords → PMFBY/seed_subsidy ranked top |
| **Voice I/O** | Mic input → STT → Analysis → TTS audio |
| **No hallucination** | Mock rules, cached quotes, real scheme data |

**Final line:** *"Scheme Saathi — schemes in your language, offline-ready, voice-first."*

---

## Exact Phrases to Speak (Copy-Paste)

### Marathi Farmer (Wardha) — 15 seconds
> मी ४२ वर्षाचा शेतकरी आहे, वर्धा, महाराष्ट्रातून. माझी वार्षिक उत्पन्न १.२ लाख रुपये आहे आणि माझ्याकडे ३ एकर जमीन आहे. मी कापूस आणि सोयाबीन पीक घेतो. मला पीक विमा आणि बीज योजनेची माहिती हवी आहे.

### Hindi Elderly Widow — 15 seconds
> मैं ६८ वर्ष की विधवा महिला हूँ, चेन्नई, तमिलनाडु से। मेरी कोई नियमित आय नहीं है और मैं अपनी बेटी के साथ रहती हूँ। मुझे पेंशन और स्वास्थ्य सहायता की आवश्यकता है।

### English Student — 10 seconds
> I am a 22-year-old student from Delhi. My family income is 3 lakh per year. I am pursuing a postgraduate degree and need scholarship information for SC category students.

---

## Demo Checklist

- [ ] Backend running on `localhost:8000` (`USE_MOCK=true`)
- [ ] UI running on `localhost:8501` (`DEMO_OFFLINE=true`)
- [ ] Sidebar shows 3 demo buttons
- [ ] Click each button → text auto-fills, language auto-switches
- [ ] "Find My Schemes" returns cached results instantly
- [ ] Scheme cards show badges, checklists, links, audio buttons
- [ ] Audio plays on card + full summary (Marathi/Hindi/English)
- [ ] No internet/API calls needed (check network tab = no requests)

---

## Files Created

```
demo_cache/
├── demo_profiles.json              # Demo input texts & languages
├── marathi_farmer_response.json    # Cached /api/analyze response (mr)
├── hindi_widow_response.json       # Cached /api/analyze response (hi)
├── english_student_response.json   # Cached /api/analyze response (en)
├── marathi_farmer_summary.mp3      # Cached TTS audio (mr)
├── hindi_widow_summary.mp3         # Cached TTS audio (hi)
└── english_student_summary.mp3     # Cached TTS audio (en)

.env                    # DEMO_OFFLINE=true added
ui/api_client.py        # Loads cached JSON + MP3 when DEMO_OFFLINE=true
ui/app.py               # Sidebar demo buttons + load_demo()
tests/test_select_keywords.py  # Keyword boost test (pmfby in top 3)
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Audio not playing | Check `demo_cache/*.mp3` exist; browser supports MP3 |
| Sidebar missing | `DEMO_OFFLINE=true` in `.env`; restart Streamlit |
| Language not switching | Check `st.session_state.language` updates on demo load |
| No cached results | Check `demo_cache/*_response.json` exist; `DEMO_OFFLINE=true` |

---

**Total demo time: 3 minutes. All offline. All multilingual. All voice-first.**