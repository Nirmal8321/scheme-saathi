"""LLM #3: Explainer - explains scheme eligibility in target language + chat."""
import json
import re
import os
import sys
from typing import Dict, Any, List, Tuple, Optional, Set

from backend.llm import call_json, translate_text
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

# Scheme ID to official link mapping (loaded from schemes.json)
SCHEME_OFFICIAL_LINKS = {}


def _load_scheme_links():
    """Load official links from schemes.json."""
    global SCHEME_OFFICIAL_LINKS
    if not SCHEME_OFFICIAL_LINKS:
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            schemes_path = os.path.join(base_dir, "data", "schemes.json")
            with open(schemes_path, "r", encoding="utf-8") as f:
                schemes = json.load(f)
                for s in schemes:
                    SCHEME_OFFICIAL_LINKS[s["id"]] = s.get("official_link", "")
        except Exception:
            pass


_load_scheme_links()


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences from response text."""
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


def _is_document_question(question: str) -> bool:
    """Check if question is about documents/papers."""
    doc_keywords = [
        "documents", "papers", "documents needed", "what documents",
        "dastavej", "dastavez", "दस्तावेज", "दस्तावेज़", "कागदपत्रे", "कागदपत्र",
        "kaagdapatra", "kaagadpatra", "documents kon-kon", "kon kon documents",
        "कौन से दस्तावेज", "क्या डॉक्यूमेंट", "what documents"
    ]
    q_lower = question.lower()
    return any(kw in q_lower for kw in doc_keywords)


def _get_document_schemes(results: List[SchemeResult]) -> List[SchemeResult]:
    """Get schemes to use for document answers:
    - First up to 2 with 'yes' verdict
    - If no 'yes', up to 2 'maybe' with 'Needs verification' reason
    - Max 3 total
    """
    doc_schemes = []

    # First, add up to 2 "yes" verdicts
    yes_results = [r for r in results if r.eligible == "yes"]
    doc_schemes.extend(yes_results[:2])

    if len(doc_schemes) < 3:
        # Add "maybe" with "Needs verification" reason
        maybe_verification = [
            r for r in results
            if r.eligible == "maybe" and "needs verification" in r.reason.lower()
        ]
        doc_schemes.extend(maybe_verification[:2])

    return doc_schemes[:3]


def _get_document_scheme_ids(results: List[SchemeResult]) -> List[str]:
    """Get scheme IDs for document answers."""
    doc_schemes = _get_document_schemes(results)
    return [r.scheme_id for r in doc_schemes]


def _build_document_answer(scheme_ids: List[str], language: str) -> Tuple[str, List[str]]:
    """Build document answer in Python from schemes.json."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    schemes_path = os.path.join(base_dir, "data", "schemes.json")

    with open(schemes_path, "r", encoding="utf-8") as f:
        schemes = json.load(f)

    scheme_map = {s["id"]: s for s in schemes}

    doc_lines = []
    sources = []

    for sid in scheme_ids:
        if sid in scheme_map:
            scheme = scheme_map[sid]
            docs = scheme.get("documents", [])
            if docs:
                doc_lines.append(f"{scheme['name']}: {', '.join(docs)}")
                sources.append(sid)

    if not doc_lines:
        return "", []

    answer_en = "Required documents:\n" + "\n".join(doc_lines)

    if language == "hi":
        answer = "आवश्यक दस्तावेज:\n" + "\n".join(
            line.replace("Required documents:", "आवश्यक दस्तावेज:")
            .replace(":", ": ")
            for line in doc_lines
        )
    elif language == "mr":
        answer = "आवश्यक कागदपत्रे:\n" + "\n".join(
            line.replace("Required documents:", "आवश्यक कागदपत्रे:")
            for line in doc_lines
        )
    else:
        answer = answer_en

    return answer, sources


def _format_money(amount: int, language: str) -> str:
    """Format money amount for the target language."""
    formatted = f"{amount:,}"
    if language in ("hi", "mr"):
        return f"{formatted} रुपये"
    return f"Rs {formatted}"


def _translate_term(term: str, language: str) -> str:
    """Translate technical terms to target language."""
    translations = {
        "hi": {
            "greenfield enterprise": "नया कारोबार",
            "greenfield project": "नई परियोजना",
            "loan": "ऋण",
            "subsidy": "सब्सिडी",
            "benefit": "लाभ",
            "eligible": "पात्र",
            "income": "आय",
            "land": "जमीन",
            "occupation": "व्यवसाय",
            "caste": "जाति",
            "category": "श्रेणी",
        },
        "mr": {
            "greenfield enterprise": "नवीन व्यवसाय",
            "greenfield project": "नवीन प्रकल्प",
            "loan": "कर्ज",
            "subsidy": "सब्सिडी",
            "benefit": "फायदा",
            "eligible": "पात्र",
            "income": "आय",
            "land": "जमीन",
            "occupation": "व्यवसाय",
            "caste": "जात",
            "category": "वर्ग",
        }
    }
    return translations.get(language, {}).get(term.lower(), term)


def _clean_explanation(text: str, scheme_id: str) -> str:
    """Remove portal names from explanation if they differ from official_link."""
    official_link = SCHEME_OFFICIAL_LINKS.get(scheme_id, "")
    if official_link:
        import urllib.parse
        try:
            domain = urllib.parse.urlparse(official_link).netloc
            if domain:
                text = text.replace(domain, "")
        except Exception:
            pass
    return text


def _should_drop_occupation_maybe(r: SchemeResult, profile: Dict[str, Any], all_results: List[SchemeResult]) -> bool:
    """Check if an occupation-unknown maybe should be dropped because profile fits other schemes better."""
    reason_lower = r.reason.lower()
    if not ("occupation" in reason_lower and ("unknown" in reason_lower or "missing" in reason_lower or "not in allowed" in reason_lower)):
        return False

    # Get the scheme's required occupations from rules
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    schemes_path = os.path.join(base_dir, "data", "schemes.json")
    try:
        with open(schemes_path, "r", encoding="utf-8") as f:
            schemes = json.load(f)
        scheme_map = {s["id"]: s for s in schemes}
        scheme = scheme_map.get(r.scheme_id)
        if not scheme:
            return False

        # Check if scheme requires specific occupation (farmer, street_vendor, student, business_owner)
        occupations = scheme.get("rules", {}).get("occupations", [])
        specific_occupations = ["farmer", "street_vendor", "student", "business_owner", "entrepreneur", "self_employed", "trader", "manufacturer", "service_provider", "shopkeeper", "artisan", "small_business"]
        requires_specific = any(occ in specific_occupations for occ in occupations)

        if not requires_specific:
            return False

        # Check if profile has other facts that fit other schemes better
        age = profile.get("age")
        gender = profile.get("gender")
        land_acres = profile.get("land_acres")

        # If age >= 60 or (gender female and no land mentioned), drop occupation-unknown maybes
        if age is not None and age >= 60:
            return True
        if gender == "female" and (land_acres is None or land_acres == 0):
            return True

    except Exception:
        pass

    return False


def select_results(results: List[SchemeResult], profile: Dict[str, Any]) -> List[SchemeResult]:
    """
    Select at most 5 results for display.
    Ranking (Python only):
    - First all "yes".
    - Then "maybe" with "Needs verification" or missing relevant profile facts.
    - Maybes with ONLY unknown occupation last, max 1.
    - Drop occupation-unknown maybes if profile has gender/age/other facts fitting other schemes better.
    - For 68yo widow with no occupation: pmjay, pm_ujjwala, pm_awas first (not namo_shetkari/pm_svanidhi).
    - Max 5 total.
    - De-duplicate by scheme_id before selecting.
    """
    # De-duplicate by scheme_id first
    seen: Set[str] = set()
    unique_results = []
    for r in results:
        if r.scheme_id not in seen:
            seen.add(r.scheme_id)
            unique_results.append(r)

    yes_results = [r for r in unique_results if r.eligible == "yes"]

    maybe_results = [r for r in unique_results if r.eligible == "maybe"]
    no_results = [r for r in unique_results if r.eligible == "no"]

    # Categorize maybes
    maybe_verification = []  # "Needs verification"
    maybe_missing_fact = []  # missing profile fact relevant to scheme
    maybe_occupation = []    # only occupation unknown

    for r in maybe_results:
        reason_lower = r.reason.lower()
        if "needs verification" in reason_lower:
            maybe_verification.append(r)
        elif "occupation" in reason_lower and ("unknown" in reason_lower or "missing" in reason_lower or "not in allowed" in reason_lower):
            maybe_occupation.append(r)
        else:
            maybe_missing_fact.append(r)

    # Drop occupation-unknown maybes if profile fits other schemes better
    filtered_occupation = []
    for r in maybe_occupation:
        if not _should_drop_occupation_maybe(r, profile, unique_results):
            filtered_occupation.append(r)
    maybe_occupation = filtered_occupation

    # Max 1 occupation maybe
    maybe_occupation = maybe_occupation[:1]

    no_results = [r for r in unique_results if r.eligible == "no"]

    # Build final list
    selected = []
    selected.extend(yes_results)
    selected.extend(maybe_verification)
    selected.extend(maybe_missing_fact)
    selected.extend(maybe_occupation)

    # Add at most 1 "no" with a clear reason
    no_with_reason = [r for r in no_results if "occupation" not in r.reason.lower() or "not in allowed" not in r.reason.lower()]
    if no_with_reason:
        selected.append(no_with_reason[0])
    elif no_results:
        selected.append(no_results[0])

    return selected[:5]


def _generate_maybe_reason(r: SchemeResult, profile: Dict[str, Any]) -> str:
    """Generate 'maybe' reason from Python rules, not LLM."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    schemes_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "schemes.json")
    try:
        with open(schemes_path, "r", encoding="utf-8") as f:
            schemes = json.load(f)
        scheme_map = {s["id"]: s for s in schemes}
        scheme = scheme_map.get(r.scheme_id)
        if not scheme:
            return r.reason

        rules = scheme.get("rules", {})
        missing_fields = []

        # Check each rule
        if rules.get("gender") and not profile.get("gender"):
            missing_fields.append("gender")
        if rules.get("min_age") and profile.get("age") is None:
            missing_fields.append("age")
        if rules.get("max_age") and profile.get("age") is None:
            missing_fields.append("age")
        if rules.get("max_income") and profile.get("annual_income") is None:
            missing_fields.append("annual income")
        if rules.get("states") and not profile.get("state"):
            missing_fields.append("state")
        if rules.get("occupations") and not profile.get("occupation"):
            missing_fields.append("occupation")
        if rules.get("needs_land") and profile.get("land_acres") is None:
            missing_fields.append("land")
        if rules.get("categories") and not profile.get("caste_category"):
            missing_fields.append("caste category")

        if missing_fields:
            # Map to verification messages
            verification_map = {
                "gender": "gender",
                "age": "age",
                "annual income": "income",
                "state": "state",
                "occupation": "occupation",
                "land": "land ownership",
                "caste category": "caste category",
            }
            verifications = [verification_map.get(f, f) for f in missing_fields]
            return "Needs verification: " + ", ".join(verifications)

        # Check for specific verification needs
        if scheme.get("id") == "pm_ujjwala":
            return "Needs verification: BPL status"
        if scheme.get("id") == "pmjay":
            return "Needs verification: SECC listing or income proof"
        if scheme.get("id") == "pm_awas":
            return "Needs verification: house ownership"
        if scheme.get("id") == "ladki_bahin":
            return "Needs verification: family income proof"
        if scheme.get("id") == "post_matric_scholarship":
            return "Needs verification: income certificate"
        if scheme.get("id") == "pm_svanidhi":
            return "Needs verification: vending certificate"

    except Exception:
        pass

    return r.reason


def select_results(results: List[SchemeResult], profile: Dict[str, Any]) -> List[SchemeResult]:
    """
    Select at most 5 results for display.
    Ranking (Python only):
    - First all "yes".
    - Then "maybe" with "Needs verification" or missing relevant profile facts.
    - Maybes with ONLY unknown occupation last, max 1.
    - Drop occupation-unknown maybes if profile has gender/age/other facts fitting other schemes better.
    - For 68yo widow with no occupation: pmjay, pm_ujjwala, pm_awas first (not namo_shetkari/pm_svanidhi).
    - Max 5 total.
    - De-duplicate by scheme_id before selecting.
    """
    # De-duplicate by scheme_id first
    seen: Set[str] = set()
    unique_results = []
    for r in results:
        if r.scheme_id not in seen:
            seen.add(r.scheme_id)
            unique_results.append(r)

    yes_results = [r for r in unique_results if r.eligible == "yes"]

    maybe_results = [r for r in unique_results if r.eligible == "maybe"]
    no_results = [r for r in unique_results if r.eligible == "no"]

    # Categorize maybes
    maybe_verification = []  # "Needs verification"
    maybe_missing_fact = []  # missing profile fact relevant to scheme
    maybe_occupation = []    # only occupation unknown

    for r in maybe_results:
        reason_lower = r.reason.lower()
        if "needs verification" in reason_lower:
            maybe_verification.append(r)
        elif "occupation" in reason_lower and ("unknown" in reason_lower or "missing" in reason_lower or "not in allowed" in reason_lower):
            maybe_occupation.append(r)
        else:
            maybe_missing_fact.append(r)

    # Drop occupation-unknown maybes if profile fits other schemes better
    filtered_occupation = []
    for r in maybe_occupation:
        if not _should_drop_occupation_maybe(r, profile, unique_results):
            filtered_occupation.append(r)
    maybe_occupation = filtered_occupation

    # Max 1 occupation maybe
    maybe_occupation = maybe_occupation[:1]

    no_results = [r for r in unique_results if r.eligible == "no"]

    # Build final list
    selected = []
    selected.extend(yes_results)
    selected.extend(maybe_verification)
    selected.extend(maybe_missing_fact)
    selected.extend(maybe_occupation)

    # Add at most 1 "no" with a clear reason
    no_with_reason = [r for r in no_results if "occupation" not in r.reason.lower() or "not in allowed" not in r.reason.lower()]
    if no_with_reason:
        selected.append(no_with_reason[0])
    elif no_results:
        selected.append(no_results[0])

    return selected[:5]


def _generate_maybe_reason(r: SchemeResult, profile: Dict[str, Any]) -> str:
    """Generate 'maybe' reason from Python rules, not LLM."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    schemes_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "schemes.json")
    try:
        with open(schemes_path, "r", encoding="utf-8") as f:
            schemes = json.load(f)
        scheme_map = {s["id"]: s for s in schemes}
        scheme = scheme_map.get(r.scheme_id)
        if not scheme:
            return r.reason

        rules = scheme.get("rules", {})
        missing_fields = []

        # Check each rule
        if rules.get("gender") and not profile.get("gender"):
            missing_fields.append("gender")
        if rules.get("min_age") and profile.get("age") is None:
            missing_fields.append("age")
        if rules.get("max_age") and profile.get("age") is None:
            missing_fields.append("age")
        if rules.get("max_income") and profile.get("annual_income") is None:
            missing_fields.append("annual income")
        if rules.get("states") and not profile.get("state"):
            missing_fields.append("state")
        if rules.get("occupations") and not profile.get("occupation"):
            missing_fields.append("occupation")
        if rules.get("needs_land") and profile.get("land_acres") is None:
            missing_fields.append("land")
        if rules.get("categories") and not profile.get("caste_category"):
            missing_fields.append("caste category")

        if missing_fields:
            # Map to verification messages
            verification_map = {
                "gender": "gender",
                "age": "age",
                "annual income": "income",
                "state": "state",
                "occupation": "occupation",
                "land": "land ownership",
                "caste category": "caste category",
            }
            verifications = [verification_map.get(f, f) for f in missing_fields]
            return "Needs verification: " + ", ".join(verifications)

        # Check for specific verification needs
        if scheme.get("id") == "pm_ujjwala":
            return "Needs verification: BPL status"
        if scheme.get("id") == "pmjay":
            return "Needs verification: SECC listing or income proof"
        if scheme.get("id") == "pm_awas":
            return "Needs verification: house ownership"
        if scheme.get("id") == "ladki_bahin":
            return "Needs verification: family income proof"
        if scheme.get("id") == "post_matric_scholarship":
            return "Needs verification: income certificate"
        if scheme.get("id") == "pm_svanidhi":
            return "Needs verification: vending certificate"

    except Exception:
        pass

    return r.reason


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
        # Use Python-generated reason for "maybe"
        reason_for_llm = _generate_maybe_reason(r, profile) if r.eligible == "maybe" else r.reason

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

    lang_name = LANGUAGE_NAMES.get(language, "English")

    system_prompt = f"""You are a government scheme explainer for Indian citizens.
Write in {lang_name} ({language} script). Use simple 6th-grade words, short sentences.

Rules:
- NEVER change the verdict (yes/no/maybe), benefit amount, or document list.
- Keep scheme names in English (PM-KISAN, Namo Shetkari, etc.).
- DO NOT include portal names/URLs in explanations (official_link provided separately).
- Write everything else in {lang_name} ({language} script).
- Money: write as "6,000 रुपये" (Hindi/Marathi) or "Rs 6,000" (English).
- Translate technical terms: "greenfield enterprise" -> "नया कारोबार" (hi) / "नवीन व्यवसाय" (mr).
- For "maybe": explain what is unknown in simple words (e.g., "tell us your age").
- "explanation": 2-3 short sentences. Benefit first, then what to do.
- "summary_text": Under 70 words. Mention which schemes may fit (by name) and ask for ONE thing, the most useful missing fact (e.g. "Do you have a BPL ration card?").
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

Target language: {language} ({LANGUAGE_NAMES.get(language, 'English')})"""

    for attempt in range(2):
        try:
            llm_result = call_json(system_prompt, user_prompt, max_tokens=2000, temperature=0.3)
            parsed = _parse_json_with_retry(json.dumps(llm_result) if isinstance(llm_result, dict) else str(llm_result))

            explanation_map = {item["scheme_id"]: item["explanation"] for item in parsed.get("results", [])}
            summary_text = parsed.get("summary_text", "")

            # Apply explanations and copy fields from schemes.json
            for r in results:
                if r.scheme_id in explanation_map:
                    # Clean explanation (remove portal names)
                    explanation = _clean_explanation(explanation_map[r.scheme_id], r.scheme_id)
                    r.explanation = explanation

                # Always copy official_link, benefit, documents, how_to_apply from schemes.json
                if r.scheme_id in SCHEME_OFFICIAL_LINKS:
                    r.official_link = SCHEME_OFFICIAL_LINKS[r.scheme_id]

                # Reload full scheme data for other fields
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                schemes_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "schemes.json")
                try:
                    with open(schemes_path, "r", encoding="utf-8") as f:
                        all_schemes = json.load(f)
                        for s in all_schemes:
                            if s["id"] == r.scheme_id:
                                r.benefit = s.get("benefit", r.benefit)
                                r.documents = s.get("documents", r.documents)
                                r.how_to_apply = s.get("how_to_apply", r.how_to_apply)
                                break
                except Exception:
                    pass

            return results, summary_text

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            if attempt == 0:
                continue
            raise ValueError(f"Failed to parse LLM response after retry: {e}")

    return results, "Check official portals for details."


def answer_chat(
    question: str,
    profile: Dict[str, Any],
    language: str,
    history: List[Dict[str, str]],
    matched_scheme_ids: Optional[List[str]] = None
) -> Tuple[str, List[str], bool]:
    """
    Answer a follow-up question about schemes.

    Args:
        question: User's question
        profile: User profile
        language: Target language
        history: Chat history
        matched_scheme_ids: Optional list of scheme IDs from match_schemes

    Returns:
        Tuple of (answer, sources, translation_failed)
    """
    lang_name = LANGUAGE_NAMES.get(language, "English")

    # Determine which schemes to use for context
    scheme_ids = matched_scheme_ids
    sources = []
    context_parts = []

    if scheme_ids:
        # Load scheme details from schemes.json
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        schemes_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "schemes.json")
        with open(schemes_path, "r", encoding="utf-8") as f:
            schemes = json.load(f)
        scheme_map = {s["id"]: s for s in schemes}

        for sid in scheme_ids:
            if sid in scheme_map:
                s = scheme_map[sid]
                sources.append(sid)
                context_parts.append(
                    f"SCHEME: {s['name']} ({sid})\n"
                    f"BENEFIT: {s.get('benefit', '')}\n"
                    f"ELIGIBILITY: {', '.join(s.get('eligibility', []))}\n"
                    f"DOCUMENTS: {', '.join(s.get('documents', []))}\n"
                    f"HOW_TO_APPLY: {s.get('how_to_apply', '')}\n"
                    f"OFFICIAL_LINK: {s.get('official_link', '')}"
                )
    else:
        # Fallback to RAG search
        rag_results = search(question, k=4)
        for result in rag_results:
            if isinstance(result, dict):
                scheme_id = result.get("scheme_id")
                text = result.get("text", "")
            else:
                scheme_id = result.metadata.get("scheme_id")
                text = result.text if hasattr(result, "text") else str(result)
            if scheme_id:
                sources.append(scheme_id)
                scheme_name = result.get("scheme_name", scheme_id) if isinstance(result, dict) else result.metadata.get("scheme_name", scheme_id)
                context_parts.append(f"SCHEME: {scheme_name} ({scheme_id})\nCONTEXT: {text}")

    context = "\n---\n".join(context_parts) if context_parts else "No relevant scheme context found."

    # Handle document questions in Python
    if _is_document_question(question) and (matched_scheme_ids or sources):
        # Get document schemes: yes first (max 2), then maybe with Needs verification (max 2), max 3 total
        doc_scheme_ids = []
        if matched_scheme_ids:
            # Use matched scheme IDs directly (they're already prioritized by select_results)
            doc_scheme_ids = matched_scheme_ids[:3]

        doc_answer, doc_sources = _build_document_answer(doc_scheme_ids, language)
        if doc_answer:
            # Use LLM only to translate/simplify
            try:
                result = translate_text(doc_answer, language, max_retries=2)

                if result.get("translation_failed"):
                    # Return English answer with translation_failed flag
                    answer = doc_answer
                    return answer, doc_sources, True

                answer = result["translated_text"]
                return answer, doc_sources, False
            except Exception as e:
                # Log the real exception and retry once
                error_type = type(e).__name__
                error_msg = str(e)
                print(f"Translation failed: {type(e).__name__}: {str(e)}", file=sys.stderr)

                # Retry once after sleeping
                try:
                    from backend.llm import _extract_retry_delay
                    retry_delay = 0
                    # If it was a 429, we'd have retry logic in translate_text
                    # For other errors, just return English with flag
                    time.sleep(1)
                except Exception:
                    pass
                return doc_answer, doc_sources, True

        # General question - use LLM
        lang_name = LANGUAGE_NAMES.get(language, "English")
        history_str = "\n".join(f"{m.get('role', 'user')}: {m.get('content', '')}" for m in history[-3:])

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
        result = call_json(
            system_prompt + "\n\nRespond with just the answer text.",
            user_prompt,
            max_tokens=500,
            temperature=0.3
        )
        if isinstance(result, dict):
            answer = result.get("answer", str(result))
        else:
            answer = str(result)
    except Exception as e:
        # Return Python-built fallback answer with error note
        fallback = "I am not sure about that. Please check the official portal for accurate information." if language == "en" else \
                   "मुझे यकीन नहीं है। कृपया आधिकारिक पोर्टल पर जाँच करें।" if language == "hi" else \
                   "मला खात्री नाही। कृपया अधिकृत पोर्टल तपासा।"
        error_note = f" (translation unavailable: {str(e)[:100]})"
        return fallback + error_note, sources, False

    return answer, sources, False


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
    text = text[:12000]

    system_prompt = f"""You are a document explainer for government documents.
Explain the document in {LANGUAGE_NAMES.get(language, 'English')} ({language} script). Use simple 6th-grade words, short sentences.
Money: "6,000 रुपये" for Hindi/Marathi, "Rs 6,000" for English.
Translate terms: "greenfield enterprise" -> "नया कारोबार" (hi) / "नवीन व्यवसाय" (mr).
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

Target language: {language} ({LANGUAGE_NAMES.get(language, 'English')})"""

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

    return "Could not generate explanation.", [], "Unknown", []


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print("Usage: python -m backend.explain \"question\" [language]")
    else:
        print("Module loaded. Use explain_results(), select_results(), answer_chat(), explain_pdf()")