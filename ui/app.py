"""Scheme Saathi - Streamlit UI."""
import os
import threading
import time
import streamlit as st
from ui.api_client import analyze, stt, tts
from ui.components import scheme_card, profile_box

# Create cache directories at runtime
os.makedirs("llm_cache", exist_ok=True)
os.makedirs("tts_cache", exist_ok=True)


@st.cache_resource
def start_backend():
    """Start FastAPI backend if not running, build index if needed."""
    import requests

    # Check if backend is already running
    try:
        resp = requests.get("http://127.0.0.1:8000/api/health", timeout=2)
        if resp.status_code == 200:
            return True
    except Exception:
        pass

    # Build ChromaDB index if missing
    chroma_path = "./chroma_db"
    if not os.path.exists(chroma_path) or not os.listdir(chroma_path):
        with st.spinner("Building knowledge base index..."):
            from backend.build_index import build_index
            build_index()

    # Start FastAPI backend in daemon thread
    def run_backend():
        import uvicorn
        config = uvicorn.Config("backend.main:app", host="127.0.0.1", port=8000, log_level="warning")
        server = uvicorn.Server(config)
        server.run()

    thread = threading.Thread(target=run_backend, daemon=True)
    thread.start()

    # Wait for /api/health up to 90 seconds
    with st.spinner("Starting the AI engine..."):
        for _ in range(90):
            try:
                resp = requests.get("http://127.0.0.1:8000/api/health", timeout=2)
                if resp.status_code == 200:
                    return True
            except Exception:
                pass
            time.sleep(1)

    st.error("Backend failed to start. Please restart the app.")
    return False


# Initialize backend at startup
start_backend()


# Page config - mobile friendly
st.set_page_config(
    page_title="Scheme Saathi",
    page_icon="🇮🇳",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for large fonts and mobile-friendly spacing
st.markdown("""
<style>
    .main { padding-top: 1rem; }
    h1 { font-size: 2.2rem !important; }
    h2 { font-size: 1.6rem !important; }
    h3 { font-size: 1.3rem !important; }
    .stButton > button {
        font-size: 1.1rem;
        padding: 0.75rem 1.5rem;
        border-radius: 10px;
    }
    .stTextArea textarea { font-size: 1.1rem !important; }
    .stSelectbox label { font-size: 1.1rem !important; }
    div[data-testid="stAudioInput"] { margin-bottom: 1rem; }
    .scheme-card { margin-bottom: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# Language mapping
LANGUAGES = {
    "English": "en",
    "हिंदी (Hindi)": "hi",
    "मराठी (Marathi)": "mr",
    "தமிழ் (Tamil)": "ta",
    "বাংলা (Bengali)": "bn",
    "తెలుగు (Telugu)": "te",
    "ગુજરાતી (Gujarati)": "gu",
    "ಕನ್ನಡ (Kannada)": "kn",
}

# Sample texts (fill text box only)
SAMPLES = {
    "Farmer in Wardha": (
        "I am a 42-year-old male farmer from Wardha, Maharashtra. "
        "My annual income is ₹1.2 lakh and I own 3 acres of land. "
        "I grow cotton and soybeans. I need help with crop insurance and seeds."
    ),
    "Woman entrepreneur": (
        "I am a 35-year-old woman from Bangalore, Karnataka. "
        "I run a small tailoring business from home. "
        "My annual income is ₹2.5 lakh. I want to expand my business and need a loan."
    ),
    "Elderly widow": (
        "I am a 68-year-old widow from Chennai, Tamil Nadu. "
        "I have no regular income and live with my daughter. "
        "I need pension and healthcare support."
    ),
}


def run_analysis():
    """Call analyze API and store result."""
    text = st.session_state.text_input.strip()
    if not text:
        st.warning("Please enter some text or record audio first.")
        return

    with st.spinner("Finding your schemes..."):
        resp = analyze(text, st.session_state.language)
        if "error" in resp:
            st.error(resp["error"])
        else:
            st.session_state.analyze_result = resp
            st.success("Done!")


def init_session_state():
    """Initialize session state variables."""
    defaults = {
        "language": "en",
        "text_input": "",
        "analyze_result": None,
        "audio_processed": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def handle_audio_input():
    """Process audio input from st.audio_input."""
    audio_value = st.session_state.get("audio_input")
    if audio_value and not st.session_state.get("audio_processed", False):
        with st.spinner("Transcribing..."):
            resp = stt(audio_value.read(), st.session_state.language)
            if "error" in resp:
                st.error(resp["error"])
            else:
                st.session_state.text_input = resp.get("text", "")
                st.success("Audio transcribed!")
        st.session_state.audio_processed = True
    elif not audio_value:
        st.session_state.audio_processed = False


def play_full_summary():
    """Play the full summary as audio."""
    result = st.session_state.get("analyze_result")
    if result and result.get("summary_text"):
        with st.spinner("Generating audio..."):
            resp = tts(result["summary_text"], st.session_state.language)
            if "error" in resp:
                st.error(resp["error"])
            else:
                st.audio(resp["audio"], format="audio/mpeg")
    else:
        st.warning("No summary to play.")


def main():
    init_session_state()
    handle_audio_input()

    # Title and tagline
    st.title("🇮🇳 Scheme Saathi")
    st.caption("Discover government schemes you're eligible for — in your language")

    # Language picker
    lang_label = st.selectbox(
        "🌐 Language",
        options=list(LANGUAGES.keys()),
        index=list(LANGUAGES.values()).index(st.session_state.language),
        key="lang_picker"
    )
    st.session_state.language = LANGUAGES[lang_label]

    st.divider()

    # Mic input
    st.subheader("🎤 Speak or Type")
    st.audio_input("Record your situation", key="audio_input")

    # Text area (editable after STT)
    st.session_state.text_input = st.text_area(
        "Your situation",
        value=st.session_state.text_input,
        height=120,
        placeholder="Describe yourself: age, gender, state, income, occupation, land, family situation...",
        label_visibility="collapsed"
    )

    # Sample buttons (fill text box only)
    st.markdown("**Quick samples:**")
    cols = st.columns(3)
    for i, (label, text) in enumerate(SAMPLES.items()):
        with cols[i]:
            if st.button(label, use_container_width=True, key=f"sample_{i}"):
                st.session_state.text_input = text
                st.rerun()

    # Analyze button
    if st.button("🔍 Find My Schemes", type="primary", use_container_width=True):
        run_analysis()

    st.divider()

    # Results section
    result = st.session_state.get("analyze_result")
    if result:
        # Profile box
        profile_box(result.get("profile", {}))

        # Scheme cards
        st.markdown("### 🎯 Your Matched Schemes")
        results = result.get("results", [])
        if results:
            for r in results:
                scheme_card(r)
        else:
            st.info("No matching schemes found. Try adding more details.")

        # Play full summary button
        if result.get("summary_text"):
            if st.button("🔊 Play Full Summary", use_container_width=True):
                play_full_summary()

    # Footer disclaimer
    st.divider()
    st.caption(
        "⚠️ **Disclaimer:** This tool provides information only. "
        "Verify all details at the official portal before applying. "
        "Scheme Saathi is not affiliated with any government agency."
    )
    st.caption(
        "📚 Knowledge base curated from official sources (link per scheme). "
        "Analysis, translation, voice and PDF reading are live."
    )


if __name__ == "__main__":
    main()