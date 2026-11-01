"""Streamlit UI components for Scheme Saathi."""
import streamlit as st
from ui.api_client import tts


def profile_box(profile: dict):
    """Display a small summary of the understood profile."""
    if not profile:
        return

    st.markdown("### 📋 Your Profile")
    cols = st.columns(3)

    fields = [
        ("👤 Gender", profile.get("gender", "—")),
        ("🎂 Age", profile.get("age", "—")),
        ("📍 State", profile.get("state", "—")),
        ("💰 Income", f"₹{profile.get('annual_income', 0):,}" if profile.get("annual_income") else "—"),
        ("👨‍🌾 Occupation", profile.get("occupation", "—")),
        ("🏠 Land (acres)", profile.get("land_acres", "—")),
        ("📜 Caste", profile.get("caste_category", "—")),
    ]

    for i, (label, value) in enumerate(fields):
        with cols[i % 3]:
            st.markdown(f"**{label}**")
            st.markdown(f"`{value}`")


def scheme_card(result: dict):
    """Display a single scheme as a card with badge, details, and TTS button."""
    verdict = result.get("eligible", "no")  # verdict is "yes", "maybe", or "no"

    if verdict == "yes":
        badge_color = "green"
        badge_text = "✅ Eligible"
    elif verdict == "maybe":
        badge_color = "orange"
        badge_text = "⚠️ Maybe: needs a check"
    else:
        badge_color = "red"
        badge_text = "❌ Not eligible"

    # Badge and scheme name
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
        <span style="background: {badge_color}; color: white; padding: 4px 12px;
                     border-radius: 20px; font-weight: 600; font-size: 14px;">
            {badge_text}
        </span>
        <h3 style="margin: 0; font-size: 1.2rem;">{result.get('scheme', 'Unknown Scheme')}</h3>
    </div>
    """, unsafe_allow_html=True)

    # Benefit
    if result.get("benefit"):
        st.markdown(f"**💰 Benefit:** {result['benefit']}")

    # Reason
    if result.get("reason"):
        st.markdown(f"**📝 Reason:** {result['reason']}")

    # Documents as checklist
    docs = result.get("documents", [])
    if docs:
        st.markdown("**📄 Documents needed:**")
        for doc in docs:
            st.checkbox(doc, key=f"doc_{result.get('scheme_id', '')}_{doc}", disabled=True)

    # How to apply
    if result.get("how_to_apply"):
        st.markdown(f"**📋 How to apply:** {result['how_to_apply']}")

    # Official link button
    if result.get("official_link"):
        st.link_button("🔗 Official Portal", result["official_link"])

    # Source quote
    if result.get("source_quote"):
        st.markdown(
            f'<small><em>📖 "{result["source_quote"]}"</em></small>',
            unsafe_allow_html=True
        )

    # Explanation
    if result.get("explanation"):
        st.markdown(f"**💡 Details:** {result['explanation']}")

    # Play audio button
    scheme_id = result.get("scheme_id", "unknown")
    if st.button("🔊 Play Audio", key=f"tts_{scheme_id}", use_container_width=True):
        explanation = result.get("explanation", "")
        benefit = result.get("benefit", "")
        text = f"{result.get('scheme', 'Scheme')}. {benefit}. {explanation}"
        text = text.strip()
        if not text:
            st.warning("No text to speak for this scheme.")
        else:
            with st.spinner("Generating audio..."):
                resp = tts(text, st.session_state.get("language", "en"))
                if "error" in resp:
                    st.error(resp["error"])
                else:
                    audio_data = resp.get("audio")
                    if audio_data:
                        st.audio(audio_data, format="audio/mp3")
                    else:
                        st.error("No audio data received")

    st.divider()