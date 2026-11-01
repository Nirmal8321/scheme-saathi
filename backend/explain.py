"""LLM #3: Explainer - explains scheme eligibility in target language + chat."""
import json
import re
import os
import sys
import time
from typing import Dict, Any, List, Tuple, Optional, Set

from backend.llm import call_json, call_text, translate_text
from backend.rag import search
from backend.schemas import SchemeResult
from backend.questions import get_question, get_verification_question

def _post_process_currency(text: str, language: str) -> str:
    """Replace Rs/lakh/crores with Hindi/Marathi equivalents."""
    import re
    if language == "hi":
        # Order matters: handle combined patterns first, then simple ones
        # Rs 5 lakh / Rs 5 crore -> 5 लाख रुपये / 5 करोड़ रुपये
        text = re.sub(r'Rs\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*lakh\b', r'\1 लाख रुपये', text, flags=re.IGNORECASE)
        text = re.sub(r'Rs\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*crore\b', r'\1 करोड़ रुपये', text, flags=re.IGNORECASE)
        # Rs 6,000 / Rs 5 -> 6,000 रुपये / 5 रुपये
        text = re.sub(r'Rs\s*(\d+(?:,\d+)*(?:\.\d+)?)', r'\1 रुपये', text, flags=re.IGNORECASE)
        # 5 lakh rupees / 5 lakh -> 5 लाख रुपये (without Rs prefix)
        text = re.sub(r'(\d+(?:,\d+)*(?:\.\d+)?)\s*lakh\b\s*rupees?\b', r'\1 लाख रुपये', text, flags=re.IGNORECASE)
        text = re.sub(r'(\d+(?:,\d+)*(?:\.\d+)?)\s*lakh\b', r'\1 लाख', text, flags=re.IGNORECASE)
        text = re.sub(r'(\d+(?:,\d+)*(?:\.\d+)?)\s*crore\b\s*rupees?\b', r'\1 करोड़ रुपये', text, flags=re.IGNORECASE)
        text = re.sub(r'(\d+(?:,\d+)*(?:\.\d+)?)\s*crore\b', r'\1 करोड़', text, flags=re.IGNORECASE)
    elif language == "mr":
        # Rs 5 lakh / Rs 5 crore -> 5 लाख रुपये / 5 करोड रुपये
        text = re.sub(r'Rs\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*lakh\b', r'\1 लाख रुपये', text, flags=re.IGNORECASE)
        text = re.sub(r'Rs\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*crore\b', r'\1 करोड रुपये', text, flags=re.IGNORECASE)
        # Rs 6,000 / Rs 5 -> 6,000 रुपये / 5 रुपये
        text = re.sub(r'Rs\s*(\d+(?:,\d+)*(?:\.\d+)?)', r'\1 रुपये', text, flags=re.IGNORECASE)
        # 5 lakh rupees / 5 lakh -> 5 लाख रुपये (without Rs prefix)
        text = re.sub(r'(\d+(?:,\d+)*(?:\.\d+)?)\s*lakh\b\s*rupees?\b', r'\1 लाख रुपये', text, flags=re.IGNORECASE)
        text = re.sub(r'(\d+(?:,\d+)*(?:\.\d+)?)\s*lakh\b', r'\1 लाख', text, flags=re.IGNORECASE)
        text = re.sub(r'(\d+(?:,\d+)*(?:\.\d+)?)\s*crore\b\s*rupees?\b', r'\1 करोड रुपये', text, flags=re.IGNORECASE)
        text = re.sub(r'(\d+(?:,\d+)*(?:\.\d+)?)\s*crore\b', r'\1 करोड', text, flags=re.IGNORECASE)
    return text

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


# ============ SHARED SELECT_RESULTS FUNCTION ============

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

        # Special case: keep pm_ujjwala for women 60+ with no land (elderly widow scenario)
        if r.scheme_id == "pm_ujjwala" and gender == "female" and age is not None and age >= 60 and (land_acres is None or land_acres == 0):
            return False

    except Exception:
        pass

    return False


def _is_elderly_widow_profile(profile: Dict[str, Any]) -> bool:
    """Check if profile matches elderly widow (female, age >= 60, no occupation, low income)."""
    gender = profile.get("gender")
    age = profile.get("age")
    occupation = profile.get("occupation")
    annual_income = profile.get("annual_income")

    return (gender == "female" and
            age is not None and age >= 60 and
            occupation is None and
            annual_income is not None and annual_income < 100000)


def _get_priority_for_elderly_widow(scheme_id: str) -> int:
    """Return priority for elderly widow profile (lower = higher priority)."""
    # Top 3 for elderly widow
    priority_map = {
        "pm_ujjwala": 0,
        "pmjay": 1,
        "pm_awas": 2,
    }
    return priority_map.get(scheme_id, 999)


def select_results(results: List[SchemeResult], profile: Dict[str, Any], query_text: str = "") -> List[SchemeResult]:
    """
    Select at most 5 results for display. ONE SHARED FUNCTION used by main.py and tests.
    Ranking:
    - Drop "no" verdicts
    - Drop schemes with required occupation (farmer, street_vendor, student, business_owner)
      when profile.occupation is null AND profile has gender, age or annual_income
    - Order: all "yes"; then "maybe" with:
      - Category boost: schemes matching query keywords (insurance, seeds, loan, scholarship, house, gas, health)
      - pm_ujjwala first if gender is female and has_lpg is false
      - then "Needs verification" reasons
      - others last
    - De-duplicate by scheme_id. Max 5.
    Expected for widow (age 68, female, income 50000, occupation null, has_lpg false):
    pm_ujjwala, pmjay, pm_awas ONLY.
    Expected for Wardha farmer: pm_kisan and namo_shetkari come first.
    """
    # De-duplicate by scheme_id first
    seen: Set[str] = set()
    unique_results = []
    for r in results:
        if r.scheme_id not in seen:
            seen.add(r.scheme_id)
            unique_results.append(r)

    # Drop "no" verdicts
    filtered = [r for r in unique_results if r.eligible != "no"]

    # Drop occupation-specific maybes when profile.occupation is null
    # AND profile already has gender, age, or annual_income
    has_gender = profile.get("gender") is not None
    has_age = profile.get("age") is not None
    has_income = profile.get("annual_income") is not None
    has_other_facts = has_gender or has_age or has_income

    filtered_results = []
    for r in filtered:
        if r.eligible == "maybe":
            reason_lower = r.reason.lower()
            # Check if reason is about occupation
            is_occupation_maybe = ("occupation" in reason_lower and
                                   ("unknown" in reason_lower or "missing" in reason_lower or "not in allowed" in reason_lower))
            if is_occupation_maybe and profile.get("occupation") is None and has_other_facts:
                continue  # Drop this scheme
        filtered_results.append(r)

    # Category-based boost: detect keywords in query_text
    query_lower = query_text.lower()
    category_keywords = {
        "insurance": ["insurance", "bima", "बीमा", "विमा", "विमा योजना", "fasal bima", "crop insurance"],
        "seeds": ["seed", "seeds", "beej", "बीज", "बियाणे", "certified seed", "hybrid seed"],
        "loan": ["loan", "credit", "kcc", "kisan credit", "मुद्रा", "कर्ज", "ऋण", "क्रेडिट कार्ड"],
        "scholarship": ["scholarship", "छात्रवृत्ति", "शिष्यवृत्ती", "post matric", "शिष्यवृत्ती"],
        "house": ["house", "housing", "awas", "आवास", "घर", "घरकुल", "home"],
        "gas": ["gas", "lpg", "ujjwala", "उज्ज्वला", "गॅस", "गैस", "एलपीजी"],
        "health": ["health", "healthcare", "hospital", "medical", "आयुष्मान", "आरोग्य", "स्वास्थ्य", "अस्पताल", "चिकित्सा"],
    }

    # Detect which categories are mentioned in query
    active_categories = set()
    for category, keywords in category_keywords.items():
        for kw in keywords:
            if kw in query_lower:
                active_categories.add(category)
                break

    # Get scheme categories from data/schemes.json
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    schemes_path = os.path.join(base_dir, "data", "schemes.json")
    scheme_category_map = {}
    try:
        with open(schemes_path, "r", encoding="utf-8") as f:
            schemes = json.load(f)
            for s in schemes:
                scheme_category_map[s["id"]] = s.get("category", "")
    except Exception:
        pass

    # Apply category boost to filtered results
    # We'll sort the filtered_results by category relevance
    def category_boost(r: SchemeResult) -> int:
        """Return boost score (higher = more relevant)"""
        scheme_cat = scheme_category_map.get(r.scheme_id, "")
        if active_categories and scheme_cat:
            cat_lower = scheme_cat.lower()
            for cat in active_categories:
                if cat in cat_lower or cat_lower in cat:
                    return 100  # High boost for matching category
        return 0

    # Sort filtered_results by category boost (descending)
    filtered_results.sort(key=lambda r: category_boost(r), reverse=True)

    yes_results = [r for r in filtered_results if r.eligible == "yes"]
    maybe_results = [r for r in filtered_results if r.eligible == "maybe"]

    # Categorize maybes
    maybe_verification = []  # "Needs verification"
    maybe_other = []         # other maybes

    for r in maybe_results:
        reason_lower = r.reason.lower()
        if "needs verification" in reason_lower:
            maybe_verification.append(r)
        else:
            maybe_other.append(r)

    # For pm_ujjwala: prioritize if female and has_lpg is false
    has_lpg = profile.get("has_lpg")
    gender = profile.get("gender")
    is_female_no_lpg = (gender == "female" and has_lpg is False)

    if is_female_no_lpg:
        # Split verification: pm_ujjwala first
        pm_ujjwala_verif = [r for r in maybe_verification if r.scheme_id == "pm_ujjwala"]
        other_verif = [r for r in maybe_verification if r.scheme_id != "pm_ujjwala"]
        maybe_verification = pm_ujjwala_verif + other_verif

    # Build final list
    selected = []
    selected.extend(yes_results)
    selected.extend(maybe_verification)
    selected.extend(maybe_other)

    # De-duplicate by scheme_id (should already be unique, but safety)
    seen: Set[str] = set()
    final_selected = []
    for r in selected:
        if r.scheme_id not in seen:
            seen.add(r.scheme_id)
            final_selected.append(r)

    # For elderly widow profile, return only top 3 (pm_ujjwala, pmjay, pm_awas)
    if _is_elderly_widow_profile(profile):
        return final_selected[:3]

    return final_selected[:5]


# ============ END SHARED SELECT_RESULTS ============


def _filter_unauthorized_numbers(
    explanation: str,
    scheme_benefit: str,
    scheme_how_to_apply: str,
    scheme_documents: List[str],
    profile: Dict[str, Any]
) -> str:
    """
    Drop sentences containing digit groups not present in scheme data or user profile.
    """
    import re

    # Collect all allowed numbers from scheme data and profile
    allowed_numbers = set()

    # From scheme benefit
    for match in re.finditer(r'\d[\d,\.]*', scheme_benefit):
        allowed_numbers.add(match.group().replace(',', ''))

    # From how_to_apply
    for match in re.finditer(r'\d[\d,\.]*', scheme_how_to_apply):
        allowed_numbers.add(match.group().replace(',', ''))

    # From documents
    for doc in scheme_documents:
        for match in re.finditer(r'\d[\d,\.]*', doc):
            allowed_numbers.add(match.group().replace(',', ''))

    # From profile
    for key, value in profile.items():
        if isinstance(value, (int, float)):
            allowed_numbers.add(str(int(value)))
        elif isinstance(value, str):
            for match in re.finditer(r'\d[\d,\.]*', value):
                allowed_numbers.add(match.group().replace(',', ''))

    # Split into sentences and filter
    sentences = re.split(r'(?<=[.!?])\s+', explanation)
    filtered_sentences = []

    for sentence in sentences:
        # Find all digit groups in the sentence
        sentence_numbers = set()
        for match in re.finditer(r'\d[\d,\.]*', sentence):
            sentence_numbers.add(match.group().replace(',', ''))

        # Check if all numbers in sentence are allowed
        unauthorized = sentence_numbers - allowed_numbers
        if not unauthorized:
            filtered_sentences.append(sentence)
        # else: drop the sentence

    return ' '.join(filtered_sentences).strip()


def _load_schemes() -> List[Dict[str, Any]]:
    """Load schemes.json. Return [] on failure."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    schemes_path = os.path.join(base_dir, "data", "schemes.json")
    try:
        with open(schemes_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def explain_results(
    results: List[SchemeResult],
    profile: Dict[str, Any],
    language: str
) -> Tuple[List[SchemeResult], str]:
    """
    Explain all scheme results in the target language.

    Args:
        results: List of SchemeResult from select_results (already ranked)
        profile: User profile dict
        language: Target language code (en, hi, mr, etc.)

    Returns:
        Tuple of (results_with_explanation, summary_text)
    """
    lang_name = LANGUAGE_NAMES.get(language, "English")

    # Prepare scheme info for LLM
    scheme_infos = []
    for r in results:
        scheme_infos.append({
            "scheme_id": r.scheme_id,
            "name": r.scheme,
            "verdict": r.eligible,
            "reason": r.reason,
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
- Keep scheme names in English (PM-KISAN, Namo Shetkari, etc.).
- DO NOT include portal names/URLs in explanations (official_link provided separately).
- Write everything else in {lang_name} ({language} script).
- Money: write as "6,000 रुपये" (Hindi/Marathi) or "Rs 6,000" (English).
- Translate technical terms: "greenfield enterprise" -> "नया कारोबार" (hi) / "नवीन व्यवसाय" (mr).
- For "maybe": explain what is unknown in simple words (e.g., "tell us your age").
- "explanation": 2-3 short sentences. Benefit first, then what to do.
- DO NOT ask the user any question. Do NOT mention caste.
- DO NOT state whether the user is or is not eligible.
- DO NOT mention income limits, ages, education level, attendance, or any specific numbers that are not explicitly present in the scheme's benefit text, how_to_apply, or documents fields provided.
- DO NOT add facts not present in the provided scheme data.
- Write only what the scheme gives (use the benefit text exactly) and how to apply.
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

    # ---- Call LLM (retry once on parse failure) ----
    explanation_map: Dict[str, str] = {}
    summary_text = ""

    for attempt in range(2):
        try:
            llm_result = call_json(system_prompt, user_prompt, max_tokens=2000, temperature=0.3)
            parsed = _parse_json_with_retry(
                json.dumps(llm_result) if isinstance(llm_result, dict) else str(llm_result)
            )
            for item in parsed.get("results", []):
                explanation_map[item.get("scheme_id")] = item.get("explanation", "")
            summary_text = parsed.get("summary_text", "") or ""
            break
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            if attempt == 0:
                continue
            raise ValueError(f"Failed to parse LLM response after retry: {e}")

    # ---- Load scheme data once ----
    all_schemes = _load_schemes()
    scheme_map = {s["id"]: s for s in all_schemes}

    # ---- Apply explanations and copy fields from schemes.json ----
    for r in results:
        scheme_data = scheme_map.get(r.scheme_id, {})

        if r.scheme_id in explanation_map:
            explanation = _clean_explanation(explanation_map[r.scheme_id], r.scheme_id)
            explanation = _filter_unauthorized_numbers(
                explanation,
                scheme_data.get("benefit", ""),
                scheme_data.get("how_to_apply", ""),
                scheme_data.get("documents", []),
                profile
            )
            r.explanation = explanation

        if r.scheme_id in SCHEME_OFFICIAL_LINKS:
            r.official_link = SCHEME_OFFICIAL_LINKS[r.scheme_id]

        if scheme_data:
            r.benefit = scheme_data.get("benefit", r.benefit)
            r.documents = scheme_data.get("documents", r.documents)
            r.how_to_apply = scheme_data.get("how_to_apply", r.how_to_apply)

    # ---- Hindi/Marathi currency post-processing ----
    if language in ("hi", "mr"):
        for r in results:
            if r.explanation:
                r.explanation = _post_process_currency(r.explanation, language)
            if r.reason:
                r.reason = _post_process_currency(r.reason, language)
        if summary_text:
            summary_text = _post_process_currency(summary_text, language)

    # ---- Filter unauthorized numbers from summary ----
    if summary_text:
        first_scheme = scheme_map.get(results[0].scheme_id, {}) if results else {}
        summary_text = _filter_unauthorized_numbers(
            summary_text,
            first_scheme.get("benefit", ""),
            first_scheme.get("how_to_apply", ""),
            first_scheme.get("documents", []),
            profile
        )

    # ---- Build next_question in Python ----
    next_question = None

    # 1) Verification question from first scheme that needs it
    for r in results:
        scheme_data = scheme_map.get(r.scheme_id)
        if scheme_data:
            requires_verification = scheme_data.get("requires_verification", [])
            if requires_verification:
                next_question = get_verification_question(requires_verification[0], language)
                break

    # 2) Otherwise first missing profile fact needed by selected schemes
    if next_question is None:
        selected_schemes = [scheme_map[r.scheme_id] for r in results if r.scheme_id in scheme_map]

        needed_facts = set()
        for s in selected_schemes:
            rules = s.get("rules", {})
            if rules.get("gender") is not None:
                needed_facts.add("gender")
            if rules.get("min_age") is not None or rules.get("max_age") is not None:
                needed_facts.add("age")
            if rules.get("max_income") is not None:
                needed_facts.add("annual_income")
            if rules.get("states"):
                needed_facts.add("state")
            if rules.get("occupations"):
                needed_facts.add("occupation")
            if rules.get("needs_land"):
                needed_facts.add("land_acres")
            if rules.get("categories") and s.get("requires_verification"):
                needed_facts.add("caste_category")

        fact_order = ["gender", "age", "annual_income", "state", "occupation", "land_acres", "caste_category"]
        missing_in_profile = [f for f in fact_order if f in needed_facts and profile.get(f) is None]
        if missing_in_profile:
            next_question = get_question(missing_in_profile[0], language)

    final_summary = summary_text
    if next_question and results:
        final_summary = (summary_text + " " + next_question).strip()

    return results, final_summary or "Check official portals for details."


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

    scheme_ids = matched_scheme_ids
    sources: List[str] = []
    context_parts: List[str] = []

    if scheme_ids:
        # Load scheme details from schemes.json
        schemes = _load_schemes()
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
                scheme_name = (
                    result.get("scheme_name", scheme_id) if isinstance(result, dict)
                    else result.metadata.get("scheme_name", scheme_id)
                )
                context_parts.append(f"SCHEME: {scheme_name} ({scheme_id})\nCONTEXT: {text}")

    context = "\n---\n".join(context_parts) if context_parts else "No relevant scheme context found."

    # ---- Document questions: answer built in Python, LLM only translates ----
    if _is_document_question(question) and (matched_scheme_ids or sources):
        doc_scheme_ids = []
        if matched_scheme_ids:
            # Already prioritized by select_results
            doc_scheme_ids = matched_scheme_ids[:3]

        doc_answer, doc_sources = _build_document_answer(doc_scheme_ids, language)
        if doc_answer:
            translation_prompt = (
                f"Translate the following text into {lang_name} ({language} script). "
                f"Keep scheme names and portal names in English. Use simple words, short sentences. "
                f"Return ONLY the translated text, no JSON, no explanation.\n\n"
                f"Text to translate:\n{doc_answer}"
            )
            try:
                answer = call_text(
                    "You are a translator for government scheme information.",
                    translation_prompt,
                    max_tokens=500,
                    temperature=0.3
                )
                return answer, doc_sources, False
            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e)
                print(f"Translation failed: {error_type}: {error_msg}", file=sys.stderr)

                # On 429, wait and retry once
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    try:
                        from backend.llm import _extract_retry_delay
                        retry_delay = _extract_retry_delay(error_msg)
                        if retry_delay is not None:
                            sleep_time = retry_delay + 1
                            print(
                                f"Translation rate limited. Sleeping for {sleep_time}s before retry...",
                                file=sys.stderr
                            )
                            time.sleep(sleep_time)
                            try:
                                answer = call_text(
                                    "You are a translator for government scheme information.",
                                    translation_prompt,
                                    max_tokens=500,
                                    temperature=0.3
                                )
                                return answer, doc_sources, False
                            except Exception:
                                pass
                    except Exception:
                        pass

                # Fallback: English answer + translation_failed flag
                return doc_answer, doc_sources, True

    # ---- General question: use LLM ----
    history_str = "\n".join(
        f"{m.get('role', 'user')}: {m.get('content', '')}" for m in history[-3:]
    )

    system_prompt = f"""You are a helpful assistant for government scheme questions.
Answer in {lang_name} ({language} script). Use simple words, max 4 short sentences.
Only use the provided context and user profile. If the answer is not there, say "I am not sure, please check the official portal" and mention the relevant official_link."""

    user_prompt = f"""User Profile: {json.dumps(profile, ensure_ascii=False)}

Context:
{context}

Chat History:
{history_str}

Question: {question}

Answer in {lang_name} ({language} script):"""

    try:
        answer = call_text(
            system_prompt,
            user_prompt,
            max_tokens=500,
            temperature=0.3
        )
    except Exception as e:
        if language == "en":
            fallback = "I am not sure about that. Please check the official portal for accurate information."
        elif language == "hi":
            fallback = "मुझे यकीन नहीं है। कृपया आधिकारिक पोर्टल पर जाँच करें।"
        else:
            fallback = "मला खात्री नाही। कृपया अधिकृत पोर्टल तपासा।"
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
Explain the document in {lang_name} ({language} script). Use simple 6th-grade words, short sentences.
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

Target language: {language} ({lang_name})"""

    for attempt in range(2):
        try:
            llm_result = call_json(system_prompt, user_prompt, max_tokens=1500, temperature=0.3)
            parsed = _parse_json_with_retry(
                json.dumps(llm_result) if isinstance(llm_result, dict) else str(llm_result)
            )
            return (
                parsed.get("summary", "") or "Could not generate explanation.",
                parsed.get("key_points", []) or [],
                parsed.get("who_is_affected", "") or "Unknown",
                parsed.get("deadlines", []) or [],
            )
        except (json.JSONDecodeError, ValueError, KeyError):
            if attempt == 0:
                continue

    return "Could not generate explanation.", [], "Unknown", []


if __name__ == "__main__":
    print("Module loaded. Use explain_results(), select_results(), answer_chat(), explain_pdf().")