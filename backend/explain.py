"""LLM #3: Explainer - explains scheme eligibility in target language + chat."""
import json
from typing import Dict, Any, List, Tuple, Optional

from backend.llm import call_json
from backend.rag import search
from backend.schemas import SchemeResult


LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "mr": "Marathi",
    "ta": "Tamil",
    "bn": "Bengali",
    "te": "Telugu",
    "gu": "Gujarati",
    "kn": "Kannada",
}


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences from response text."""
    import re
    pattern = r'^```(?:json)?\s*\n?(.*?)\n?```$'
    match = re.match(pattern, text.strip(), re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def _parse_json_with_retry(text: str) -> Dict[str, Any]:
    """Parse JSON with one retry after stripping code fences."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        cleaned = _strip_code_fences(text)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON after retry: {e}")


def select_results(results: List[SchemeResult]) -> List[SchemeResult]:
    """
    Select at most 5 results for display.
    Priority: all "yes" first, then "maybe" (verification/missing-field first, occupation-unknown last, max 2),
    then at most 1 "no" with its reason.
    """
    yes_results = [r for r in results if r.eligible == "yes"]

    maybe_results = [r for r in results if r.eligible == "maybe"]

    # Separate maybes by reason type
    maybe_verification = []  # "Needs verification" reasons
    maybe_missing_field = []  # other missing fields
    maybe_occupation = []  # occupation unknown

    for r in maybe_results:
        reason_lower = r.reason.lower()
        if "needs verification" in reason_lower:
            maybe_verification.append(r)
        elif "occupation" in reason_lower and ("unknown" in reason_lower or "missing" in reason_lower or "not in allowed" in reason_lower):
            maybe_occupation.append(r)
        else:
            maybe_missing_field.append(r)

    no_results = [r for r in results if r.eligible == "no"]

    # Build final list: yes + maybe_verification + maybe_missing_field + maybe_occupation (max 2) + no (max 1)
    selected = []
    selected.extend(yes_results)
    selected.extend(maybe_verification)
    selected.extend(maybe_missing_field)
    selected.extend(maybe_occupation[:2])  # max 2 occupation-unknown maybes

    # Add at most 1 "no" with its reason
    if no_results:
        # Prefer a "no" with a clear reason (not just occupation mismatch)
        no_with_reason = [r for r in no_results if "occupation" not in r.reason.lower() or "not in allowed" not in r.reason.lower()]
        if no_with_reason:
            selected.append(no_with_reason[0])
        else:
            selected.append(no_results[0])

    return selected[:5]


def explain_results(
    results: List[SchemeResult],
    profile: Dict[str, Any],
    language: str
) -> Tuple[List[SchemeResult], str]:
    """
    Explain all scheme results in the target language.

    Args:
        results: List of SchemeResult from match_schemes (without explanation)
        profile: User profile dict
        language: Target language code (en, hi, mr, etc.)

    Returns:
        Tuple of (results_with_explanation, summary_text)
    """
    lang_name = LANGUAGE_NAMES.get(language, "English")

    # Prepare scheme info for LLM
    scheme_infos = []
    for r in results:
        # Convert reason to simple terms for LLM
        reason_for_llm = r.reason
        # For "maybe" with "Needs verification", extract what needs verification
        if r.eligible == "maybe" and "needs verification" in r.reason.lower():
            reason_for_llm = r.reason

        scheme_infos.append({
            "scheme_id": r.scheme_id,
            "name": r.scheme,
            "verdict": r.eligible,
            "reason": reason_for_llm,
            "benefit": r.benefit,
            "documents": r.documents,
            "how_to_apply": r.how_to_apply,
            "official_link": r.official_link,
            "source_quote": r.source_quote,
        })

    system_prompt = f"""You are a government scheme explainer for Indian citizens.
Write in {lang_name} ({language} script). Use simple 6th-grade words, short sentences.

Rules:
- NEVER change the verdict (yes/no/maybe), benefit amount, or document list.
- Keep scheme names and portal names in English (PM-KISAN, pmkisan.gov.in).
- Write everything else in {lang_name} ({language} script).
- For "maybe": explain what is unknown in simple words (e.g., "tell us your age").
- "explanation": 2-3 short sentences. Benefit first, then what to do.
- "summary_text": Under 70 words. Mention how many schemes user likely qualifies for and which one first.
- Return ONLY valid JSON with this structure:
{{
  "results": [
    {{"scheme_id": "...", "explanation": "..."}},
    ...
  ],
  "summary_text": "..."
}}"""

    user_prompt = f"""User Profile: {json.dumps(profile, ensure_ascii=False)}
Schemes:
{json.dumps(scheme_infos, ensure_ascii=False, indent=2)}

Target language: {language} ({lang_name})"""

    # Try once, then retry once on bad JSON
    for attempt in range(2):
        try:
            llm_result = call_json(system_prompt, user_prompt, max_tokens=2000, temperature=0.3)
            parsed = _parse_json_with_retry(json.dumps(llm_result) if isinstance(llm_result, dict) else str(llm_result))

            # Update results with explanations
            explanation_map = {item["scheme_id"]: item["explanation"] for item in parsed.get("results", [])}
            summary_text = parsed.get("summary_text", "")

            for r in results:
                if r.scheme_id in explanation_map:
                    r.explanation = explanation_map[r.scheme_id]

            return results, summary_text

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            if attempt == 0:
                continue  # Retry once
            raise ValueError(f"Failed to parse LLM response after retry: {e}")

    # Fallback: return results without explanations
    return results, "Check official portals for details."


def answer_chat(
    question: str,
    profile: Dict[str, Any],
    language: str,
    history: List[Dict[str, str]]
) -> Tuple[str, List[str]]:
    """
    Answer a follow-up question about schemes.

    Args:
        question: User's question
        profile: User profile
        language: Target language
        history: Chat history

    Returns:
        Tuple of (answer, sources)
    """
    lang_name = LANGUAGE_NAMES.get(language, "English")

    # Search for relevant context
    rag_results = search(question, k=4)

    # Build context
    context_parts = []
    sources = []
    for result in rag_results:
        # Handle both mock dict format and real chunk objects
        if isinstance(result, dict):
            scheme_id = result.get("scheme_id")
            score = result.get("score", 0.0)
            text = result.get("text", "")
        else:
            scheme_id = result.metadata.get("scheme_id")
            score = 1.0 - getattr(result, "distance", 0.0)
            text = result.text if hasattr(result, "text") else str(result)

        if scheme_id:
            sources.append(scheme_id)
            context_parts.append(
                f"SCHEME: {result.get('scheme_name', scheme_id) if isinstance(result, dict) else result.metadata.get('scheme_name', scheme_id)} ({scheme_id})\n"
                f"CONTEXT: {text}"
            )

    context = "\n---\n".join(context_parts) if context_parts else "No relevant scheme context found."

    # Build history string
    history_str = ""
    for msg in history[-3:]:  # Last 3 messages
        role = msg.get("role", "user")
        content = msg.get("content", "")
        history_str += f"{role}: {content}\n"

    system_prompt = f"""You are a helpful assistant for government scheme questions.
Answer in {lang_name} ({language} script). Use simple words, max 4 short sentences.
Only use the provided context and user profile. If the answer is not there, say "I am not sure, please check the official portal" and mention the relevant official_link.
Return ONLY the answer text, no JSON."""

    user_prompt = f"""User Profile: {json.dumps(profile, ensure_ascii=False)}

Context:
{context}

Chat History:
{history_str}

Question: {question}

Answer in {lang_name} ({language} script):"""

    try:
        # Use LLM with lower temperature for factual answers
        result = call_json(
            system_prompt + "\n\nRespond with just the answer text.",
            user_prompt,
            max_tokens=500,
            temperature=0.3
        )
        # The LLM returns JSON, but we want plain text
        if isinstance(result, dict):
            answer = result.get("answer", str(result))
        else:
            answer = str(result)
    except Exception:
        answer = f"I am not sure about that. Please check the official portals for accurate information." if language == "en" else \
                 f"मुझे यकीन नहीं है। कृपया आधिकारिक पोर्टल पर जाँच करें।" if language == "hi" else \
                 f"मला खात्री नाही। कृपया अधिकृत पोर्टल तपासा।"

    return answer, sources


def explain_pdf(text: str, language: str) -> Tuple[str, List[str], str, List[str]]:
    """
    Explain a PDF document in the target language.

    Args:
        text: Extracted text from PDF
        language: Target language

    Returns:
        Tuple of (summary, key_points, who_is_affected, deadlines)
    """
    lang_name = LANGUAGE_NAMES.get(language, "English")

    # Trim text to reasonable length
    text = text[:12000]

    system_prompt = f"""You are a document explainer for government documents.
Explain the document in {lang_name} ({language} script). Use simple 6th-grade words, short sentences.
Return ONLY valid JSON with this structure:
{{
  "summary": "plain language summary in {language} (2-3 sentences)",
  "key_points": ["point 1", "point 2", "..."],
  "who_is_affected": "who this document affects (1 sentence)",
  "deadlines": ["deadline 1", "deadline 2"]
}}
Keep names of schemes and portals in English."""

    user_prompt = f"""Document text:
{text}

Target language: {language} ({lang_name})"""

    for attempt in range(2):
        try:
            llm_result = call_json(system_prompt, user_prompt, max_tokens=1500, temperature=0.3)
            parsed = _parse_json_with_retry(json.dumps(llm_result) if isinstance(llm_result, dict) else str(llm_result))

            summary = parsed.get("summary", "")
            key_points = parsed.get("key_points", [])
            who_is_affected = parsed.get("who_is_affected", "")
            deadlines = parsed.get("deadlines", [])

            return summary, key_points[:5], who_is_affected, deadlines

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            if attempt == 0:
                continue
            raise ValueError(f"Failed to parse PDF explanation after retry: {e}")

    # Fallback
    return "Could not generate explanation.", [], "Unknown", []


if __name__ == "__main__":
    # Quick test
    import sys
    if len(sys.argv) > 1:
        print("Usage: python -m backend.explain \"question\" [language]")
    else:
        print("Module loaded. Use explain_results(), select_results(), answer_chat(), explain_pdf()")