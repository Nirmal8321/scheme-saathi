"""LLM #1: Profile extractor - extracts user profile from free text input."""
import json
import re
from typing import Dict, Any, List, Tuple, Optional
from backend.schemas import Profile
from backend.llm import call_json


# Number words in different languages/scripts
INCOME_WORDS = {
    # Hindi/Devanagari
    "हजार": 1000,
    "हज़ार": 1000,
    "लाख": 100000,
    "करोड़": 10000000,
    # Marathi/Devanagari
    "हजार": 1000,
    "लाख": 100000,
    "कोटी": 10000000,
    # Latin script (transliterated)
    "hajar": 1000,
    "hazaar": 1000,
    "lakh": 100000,
    "lac": 100000,
    "crore": 10000000,
    "k": 1000,
    "thousand": 1000,
    "million": 1000000,
}


OCCUPATION_MAP = {
    # Hindi
    "किसान": "farmer",
    "शेतकरी": "farmer",
    "व्यापारी": "trader",
    "व्यवसायी": "business_owner",
    "नौकरी": "employee",
    "सेवा": "employee",
    "विद्यार्थी": "student",
    "छात्र": "student",
    "गृहिणी": "homemaker",
    "मजदूर": "laborer",
    "ड्राइवर": "driver",
    # Marathi
    "शेतकरी": "farmer",
    "व्यवसायी": "business_owner",
    "नोकरी": "employee",
    "विद्यार्थी": "student",
    "गृहिणी": "homemaker",
    "कामगार": "laborer",
    "वाहन चालक": "driver",
    # Latin script (transliterated Hindi/Marathi)
    "shetkari": "farmer",
    "kisan": "farmer",
    "kheti": "farmer",
    "vyapari": "trader",
    "vyavsayi": "business_owner",
    "naukri": "employee",
    "seva": "employee",
    "vidyarthi": "student",
    "student": "student",
    "grihini": "homemaker",
    "housewife": "homemaker",
    "mazdur": "laborer",
    "worker": "laborer",
    "driver": "driver",
    "vendor": "street_vendor",
    "street vendor": "street_vendor",
    "hawker": "street_vendor",
    "entrepreneur": "entrepreneur",
    # English
    "farmer": "farmer",
    "trader": "trader",
    "business owner": "business_owner",
    "business": "business_owner",
    "employee": "employee",
    "job": "employee",
    "student": "student",
    "homemaker": "homemaker",
    "housewife": "homemaker",
    "laborer": "laborer",
    "worker": "laborer",
    "driver": "driver",
    "vendor": "street_vendor",
    "street vendor": "street_vendor",
    "hawker": "street_vendor",
    "entrepreneur": "entrepreneur",
}


# District to State mapping for state inference
DISTRICT_TO_STATE = {
    # Maharashtra
    "wardha": "Maharashtra",
    "नागपूर": "Maharashtra",
    "नागपुर": "Maharashtra",
    "पुणे": "Maharashtra",
    "पुणे": "Maharashtra",
    "मुंबई": "Maharashtra",
    "मुंबई": "Maharashtra",
    "ठाणे": "Maharashtra",
    "नाशिक": "Maharashtra",
    "नाशिक": "Maharashtra",
    "औरंगाबाद": "Maharashtra",
    "सोलापूर": "Maharashtra",
    "कोल्हापूर": "Maharashtra",
    "सांगली": "Maharashtra",
    "सातारा": "Maharashtra",
    "अहमदनगर": "Maharashtra",
    "जळगाव": "Maharashtra",
    "नंदूरबार": "Maharashtra",
    "धुळे": "Maharashtra",
    "नांदेड": "Maharashtra",
    "परभणी": "Maharashtra",
    "हिंगोली": "Maharashtra",
    "बुलढाणा": "Maharashtra",
    "अकोला": "Maharashtra",
    "वाशिम": "Maharashtra",
    "यवतमाळ": "Maharashtra",
    "अमरावती": "Maharashtra",
    "गडचिरोली": "Maharashtra",
    "चंद्रपूर": "Maharashtra",
    "गोंदिया": "Maharashtra",
    "भंडारा": "Maharashtra",
    # Other major cities
    "दिल्ली": "Delhi",
    "बेंगलुरु": "Karnataka",
    "बंगलोर": "Karnataka",
    "हैदराबाद": "Telangana",
    "चेन्नई": "Tamil Nadu",
    "कोलकाता": "West Bengal",
    "अहमदाबाद": "Gujarat",
    "सूरत": "Gujarat",
    "जयपुर": "Rajasthan",
    "लखनऊ": "Uttar Pradesh",
    "कानपुर": "Uttar Pradesh",
    "नोएडा": "Uttar Pradesh",
    "गुरुग्राम": "Haryana",
    "गुड़गांव": "Haryana",
    "पटना": "Bihar",
    "भोपाल": "Madhya Pradesh",
    "इंदौर": "Madhya Pradesh",
    "कोच्चि": "Kerala",
    "तिरुवनंतपुरम": "Kerala",
    "गुवाहाटी": "Assam",
    "शिमला": "Himachal Pradesh",
    "देहरादून": "Uttarakhand",
    "रांची": "Jharkhand",
    "रायपुर": "Chhattisgarh",
    # Latin script versions
    "nagpur": "Maharashtra",
    "pune": "Maharashtra",
    "mumbai": "Maharashtra",
    "thane": "Maharashtra",
    "nashik": "Maharashtra",
    "aurangabad": "Maharashtra",
    "solapur": "Maharashtra",
    "kolhapur": "Maharashtra",
    "sangli": "Maharashtra",
    "satara": "Maharashtra",
    "ahmednagar": "Maharashtra",
    "jalgaon": "Maharashtra",
    "nandurbar": "Maharashtra",
    "dhule": "Maharashtra",
    "nanded": "Maharashtra",
    "parbhani": "Maharashtra",
    "hingoli": "Maharashtra",
    "buldhana": "Maharashtra",
    "akola": "Maharashtra",
    "washim": "Maharashtra",
    "yavatmal": "Maharashtra",
    "amravati": "Maharashtra",
    "gadchiroli": "Maharashtra",
    "chandrapur": "Maharashtra",
    "gondia": "Maharashtra",
    "bhandara": "Maharashtra",
    "delhi": "Delhi",
    "bangalore": "Karnataka",
    "hyderabad": "Telangana",
    "chennai": "Tamil Nadu",
    "kolkata": "West Bengal",
    "ahmedabad": "Gujarat",
    "surat": "Gujarat",
    "jaipur": "Rajasthan",
    "lucknow": "Uttar Pradesh",
    "kanpur": "Uttar Pradesh",
    "noida": "Uttar Pradesh",
    "gurgaon": "Haryana",
    "patna": "Bihar",
    "bhopal": "Madhya Pradesh",
    "indore": "Madhya Pradesh",
    "kochi": "Kerala",
    "thiruvananthapuram": "Kerala",
    "guwahati": "Assam",
    "shimla": "Himachal Pradesh",
    "dehradun": "Uttarakhand",
    "ranchi": "Jharkhand",
    "raipur": "Chhattisgarh",
}


STATE_MAP = {
    # Hindi
    "महाराष्ट्र": "Maharashtra",
    "दिल्ली": "Delhi",
    "उत्तर प्रदेश": "Uttar Pradesh",
    "बिहार": "Bihar",
    "पश्चिम बंगाल": "West Bengal",
    "तमिलनाडु": "Tamil Nadu",
    "कर्नाटक": "Karnataka",
    "आंध्र प्रदेश": "Andhra Pradesh",
    "तेलंगाना": "Telangana",
    "गुजरात": "Gujarat",
    "राजस्थान": "Rajasthan",
    "मध्य प्रदेश": "Madhya Pradesh",
    "पंजाब": "Punjab",
    "हरियाणा": "Haryana",
    "केरल": "Kerala",
    "ओडिशा": "Odisha",
    "झारखंड": "Jharkhand",
    "छत्तीसगढ़": "Chhattisgarh",
    "उत्तराखंड": "Uttarakhand",
    "हिमाचल प्रदेश": "Himachal Pradesh",
    "असम": "Assam",
    # Marathi
    "महाराष्ट्र": "Maharashtra",
    "दिल्ली": "Delhi",
    "उत्तर प्रदेश": "Uttar Pradesh",
    "बिहार": "Bihar",
    "तमिळनाडू": "Tamil Nadu",
    "कर्नाटक": "Karnataka",
    "आंध्र प्रदेश": "Andhra Pradesh",
    "तेलंगाणा": "Telangana",
    "गुजरात": "Gujarat",
    "राजस्थान": "Rajasthan",
    "मध्य प्रदेश": "Madhya Pradesh",
    "पंजाब": "Punjab",
    "हरियाणा": "Haryana",
    "केरळ": "Kerala",
    "ओडिशा": "Odisha",
    "झारखंड": "Jharkhand",
    "छत्तीसगढ": "Chhattisgarh",
    # English (already normalized)
    "maharashtra": "Maharashtra",
    "delhi": "Delhi",
    "uttar pradesh": "Uttar Pradesh",
    "bihar": "Bihar",
    "west bengal": "West Bengal",
    "tamil nadu": "Tamil Nadu",
    "karnataka": "Karnataka",
    "andhra pradesh": "Andhra Pradesh",
    "telangana": "Telangana",
    "gujarat": "Gujarat",
    "rajasthan": "Rajasthan",
    "madhya pradesh": "Madhya Pradesh",
    "punjab": "Punjab",
    "haryana": "Haryana",
    "kerala": "Kerala",
    "odisha": "Odisha",
    "jharkhand": "Jharkhand",
    "chhattisgarh": "Chhattisgarh",
    "uttarakhand": "Uttarakhand",
    "himachal pradesh": "Himachal Pradesh",
    "assam": "Assam",
}


DISTRICT_MAP = {
    # Maharashtra districts (common)
    "वर्धा": "Wardha",
    "नागपूर": "Nagpur",
    "नागपुर": "Nagpur",
    "पुणे": "Pune",
    "मुंबई": "Mumbai",
    "ठाणे": "Thane",
    "नाशिक": "Nashik",
    "औरंगाबाद": "Aurangabad",
    "सोलापूर": "Solapur",
    "कोल्हापूर": "Kolhapur",
    "सांगली": "Sangli",
    "सातारा": "Satara",
    "अहमदनगर": "Ahmednagar",
    "जळगाव": "Jalgaon",
    "नंदूरबार": "Nandurbar",
    "धुळे": "Dhule",
    "नांदेड": "Nanded",
    "परभणी": "Parbhani",
    "हिंगोली": "Hingoli",
    "बुलढाणा": "Buldhana",
    "अकोला": "Akola",
    "वाशिम": "Washim",
    "यवतमाळ": "Yavatmal",
    "अमरावती": "Amravati",
    "गडचिरोली": "Gadchiroli",
    "चंद्रपूर": "Chandrapur",
    "गोंदिया": "Gondia",
    "भंडारा": "Bhandara",
    # Latin script
    "wardha": "Wardha",
    "nagpur": "Nagpur",
    "pune": "Pune",
    "mumbai": "Mumbai",
    "thane": "Thane",
    "nashik": "Nashik",
    "aurangabad": "Aurangabad",
    "solapur": "Solapur",
    "kolhapur": "Kolhapur",
    "sangli": "Sangli",
    "satara": "Satara",
    "ahmednagar": "Ahmednagar",
    "jalgaon": "Jalgaon",
    "nandurbar": "Nandurbar",
    "dhule": "Dhule",
    "nanded": "Nanded",
    "parbhani": "Parbhani",
    "hingoli": "Hingoli",
    "buldhana": "Buldhana",
    "akola": "Akola",
    "washim": "Washim",
    "yavatmal": "Yavatmal",
    "amravati": "Amravati",
    "gadchiroli": "Gadchiroli",
    "chandrapur": "Chandrapur",
    "gondia": "Gondia",
    "bhandara": "Bhandara",
}


GENDER_MAP = {
    # Hindi
    "पुरुष": "male",
    "महिला": "female",
    "स्त्री": "female",
    "लडका": "male",
    "लडकी": "female",
    # Marathi
    "पुरुष": "male",
    "स्त्री": "female",
    "मुलगा": "male",
    "मुलगी": "female",
    # English
    "male": "male",
    "female": "female",
    "man": "male",
    "woman": "female",
    "boy": "male",
    "girl": "female",
    "m": "male",
    "f": "female",
}


CASTE_MAP = {
    # Hindi
    "सामान्य": "General",
    "अनुसूचित जाति": "SC",
    "अनुसूचित जनजाति": "ST",
    "अन्य पिछड़ा वर्ग": "OBC",
    "अन्य पिछडा वर्ग": "OBC",
    # Marathi
    "सामान्य": "General",
    "अनुसूचित जाती": "SC",
    "अनुसूचित जमाती": "ST",
    "इतर मागास वर्ग": "OBC",
    # English
    "general": "General",
    "sc": "SC",
    "st": "ST",
    "obc": "OBC",
    "ews": "EWS",
}


# Female gender indicators from grammar and vocabulary
FEMALE_INDICATORS = [
    # Hindi feminine verb forms
    "चलती हूं", "करती हूं", "रहती हूं", "खाती हूं", "पीती हूं",
    "जाती हूं", "आती हूं", "बोलती हूं", "लिखती हूं", "पढ़ती हूं",
    "करती हूँ", "रहती हूँ", "चलती हूँ",
    # Marathi feminine verb forms
    "चालते", "करते", "राहते", "खाते", "पिते", "जाते", "येते",
    "बोलते", "लिहिते", "शिकते",
    # Explicit female words
    "महिला", "स्त्री", "लडकी", "लड़की", "बेटी", "पत्नी", "विधवा",
    "विदवा", "विधवा", "महिला", "औरत", "लडकी", "लडकी",
    "widow", "woman", "girl", "female", "daughter", "wife",
    "widowed", "लडकी", "लड़की",
    # Marathi female words
    "मुलगी", "बायको", "विधवा", "स्त्री", "महिला", "पत्नी",
]

MALE_INDICATORS = [
    # Hindi masculine verb forms
    "चलता हूं", "करता हूं", "रहता हूं", "खाता हूं", "पीता हूं",
    "जाता हूं", "आता हूं", "बोलता हूं", "लिखता हूं", "पढ़ता हूं",
    "करता हूँ", "रहता हूँ", "चलता हूँ",
    # Marathi masculine verb forms
    "चालतो", "करतो", "राहतो", "खातो", "पितो", "जातो", "येईतो",
    "बोलतो", "लिहितो", "शिकतो",
    # Explicit male words
    "पुरुष", "लडका", "लड़का", "बेटा", "पति", "विधुर",
    "widower", "man", "boy", "male", "son", "husband",
    # Marathi male words
    "मुलगा", "नवरा", "विधुर", "पुरुष", "पती",
]

# Additional gender indicators for post-check (from task requirements)
FEMALE_POST_CHECK_INDICATORS = [
    # Latin script (Hindi/Marathi transliterated)
    "vidhwa", "vidhva", "mahila", "stree", "patni", "beti", "ladki", "bahin",
    "widow", "woman", "female",
    # Hindi feminine verb forms (first person)
    "chalti hoon", "rehti hoon", "karti hoon", "karte hoon",  # "karte hoon" explicitly NOT female per requirements
    # Marathi feminine verb forms
    "chalte", "karte", "rahte", "ahhe",  # "aahe" can be female in some contexts
    # Devanagari
    "विधवा", "महिला", "स्त्री", "पत्नी", "बेटी", "मुलगी", "लाडकी", "लडकी",
    "रहती हूँ", "चलती हूँ", "करती हूँ",
]

MALE_POST_CHECK_INDICATORS = [
    # Latin script masculine forms
    "chalta hoon", "rehta hoon", "karta hoon", "vikto", "karto", "kartey",
    "vidhur", "pati", "man", "male",
    "ahe ek", "mi ek",  # "ahe ek", "mi ek mahila" context
    # Devanagari
    "पुरुष",
]


def _gender_post_check(text: str, llm_gender: Optional[str]) -> Optional[str]:
    """
    Deterministic gender post-check on original text (lowercase).
    Overrides LLM value if rules match. If no rule matches and LLM said male/female, set to null.
    Uses word-boundary-aware matching to avoid false positives (e.g., "stree" in "street").
    """
    import re
    text_lower = text.lower()

    # Check female indicators with word boundaries
    for indicator in FEMALE_POST_CHECK_INDICATORS:
        # Use word boundaries for single words, but allow partial for verb forms
        if ' ' in indicator:
            # Multi-word phrase - check as substring
            if indicator in text_lower:
                return "female"
        else:
            # Single word - use word boundary
            pattern = rf'\b{re.escape(indicator)}\b'
            if re.search(pattern, text_lower):
                return "female"

    # Check male indicators with word boundaries
    for indicator in MALE_POST_CHECK_INDICATORS:
        if ' ' in indicator:
            if indicator in text_lower:
                return "male"
        else:
            pattern = rf'\b{re.escape(indicator)}\b'
            if re.search(pattern, text_lower):
                return "male"

    # No rule matched - if LLM said male or female, set to null (no guessing)
    if llm_gender in ("male", "female"):
        return None

    return llm_gender


def _income_post_check(text: str, annual_income: Optional[int], income_note: Optional[str]) -> Tuple[Optional[int], Optional[str], bool]:
    """
    Income post-check on original text.
    NEVER extracts numbers from text - only checks for daily-income markers.
    If text has daily-income marker (rozache, roz, daily, per day, din ka, प्रतिदिन, रोज),
    set annual_income to null and fill income_note with the phrase.

    Before applying the below-1000 guard, if annual_income is a bare number,
    check for number words (hazar/hajar/हजार, lakh/lac/लाख, crore/करोड/करोड़)
    near that number in the original text and multiply accordingly.

    Returns (annual_income, income_note, should_add_to_missing)
    """
    import re
    text_lower = text.lower()

    # Daily/irregular income indicators
    daily_indicators = ["rozache", "daily", "per day", "roz", "din ka", "प्रतिदिन", "रोज"]

    # Check if text has daily indicator
    has_daily = any(indicator in text_lower for indicator in daily_indicators)

    if has_daily:
        # Extract the original phrase for income_note - look for number AFTER the indicator
        for indicator in daily_indicators:
            if indicator in text_lower:
                idx = text_lower.find(indicator)
                # Look for number AFTER the indicator (within 30 chars)
                after_start = idx + len(indicator)
                after_end = min(len(text_lower), after_start + 30)
                after_text = text_lower[after_start:after_end]
                nums = re.findall(r'\d+(?:[.,-]\d+)?', after_text)
                if nums:
                    # Return just "number indicator" as the note
                    return None, f"{nums[0]} {indicator}", True

                # Fallback: look before (for patterns like "500-700 rozache")
                before_start = max(0, idx - 20)
                before_text = text_lower[before_start:idx]
                nums_before = re.findall(r'\d+(?:[.,-]\d+)?', before_text)
                if nums_before:
                    return None, f"{nums_before[-1]} {indicator}", True

        return None, "daily income mentioned", True

    # No daily indicator - keep the LLM's annual_income as-is
    # But first, if annual_income is a bare number, check for nearby number words to multiply
    if annual_income is not None and annual_income < 10000000:  # reasonable upper bound
        # Look for number words near the annual_income value in the text
        # The LLM might have returned just the bare number (e.g., 50 for "50 hazar")
        # Check if the number appears near hazar/lakh/crore in the text
        income_str = str(annual_income)
        # Find all occurrences of this number in the text
        for match in re.finditer(rf'\b{re.escape(income_str)}\b', text_lower):
            idx = match.start()
            # Check context around this number (50 chars before and after)
            context_start = max(0, idx - 50)
            context_end = min(len(text_lower), idx + len(income_str) + 50)
            context = text_lower[context_start:context_end]

            # Check for number words in context using word boundaries to avoid false matches
            multiplier = 1
            if any(re.search(rf'\b{re.escape(w)}\b', context) for w in ["hazar", "hajar", "हजार", "हज़ार", "thousand"]):
                multiplier = 1000
            elif any(re.search(rf'\b{re.escape(w)}\b', context) for w in ["lakh", "लाख", "lac"]):
                multiplier = 100000
            elif any(re.search(rf'\b{re.escape(w)}\b', context) for w in ["crore", "करोड", "करोड़", "कोटी"]):
                multiplier = 10000000

            if multiplier > 1:
                annual_income = annual_income * multiplier
                break  # Use first match with multiplier

    # Add sanity guard: if annual_income is below 1000, it's likely wrong
    if annual_income is not None and annual_income < 1000:
        return None, None, True

    return annual_income, income_note, False


def _compute_missing_fields(profile_data: Dict[str, Any]) -> List[str]:
    """Compute missing_fields from null fields in profile data."""
    important_fields = ["age", "gender", "annual_income", "caste_category", "occupation"]
    return [field for field in important_fields if profile_data.get(field) is None]


def _apply_post_processing(text: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply deterministic post-processing checks to profile data.
    This runs on both LLM and fallback extraction results.
    """
    # POST-CHECK 1: Gender - deterministic override from original text
    profile_data["gender"] = _gender_post_check(text, profile_data.get("gender"))

    # POST-CHECK 2: Income - check for daily/irregular income in original text
    profile_data["annual_income"], profile_data["income_note"], income_missing = _income_post_check(
        text, profile_data.get("annual_income"), profile_data.get("income_note")
    )

    # POST-CHECK 3: Occupation fallback - if LLM occupation is null, set from keywords
    if profile_data.get("occupation") is None:
        profile_data["occupation"] = _normalize_occupation(text)

    # Track if income was set to missing due to sanity guard
    if income_missing and "annual_income" not in [k for k, v in profile_data.items() if v is None]:
        # Will be added to missing_fields by _compute_missing_fields
        pass

    return profile_data


def _normalize_text(text: str) -> str:
    """Normalize text for processing."""
    return text.strip()


def _extract_number(text: str) -> Optional[float]:
    """Extract first number from text (handles Devanagari digits too)."""
    # Devanagari digits
    devanagari_digits = {
        '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
        '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'
    }
    for dev, eng in devanagari_digits.items():
        text = text.replace(dev, eng)

    # Find numbers (including decimals)
    matches = re.findall(r'\d+(?:\.\d+)?', text)
    if matches:
        return float(matches[0])
    return None


def _parse_income(text: str) -> Tuple[Optional[int], Optional[str]]:
    """
    Parse income from text.
    Returns (annual_income, income_note).
    Only fills annual_income if annual or monthly figure given.
    For daily/irregular ranges, returns (None, original_phrase).
    """
    text_lower = text.lower()

    # First try to find explicit number with unit (annual/monthly)
    for word, multiplier in INCOME_WORDS.items():
        pattern = rf'(\d+(?:\.\d+)?)\s*{re.escape(word)}'
        match = re.search(pattern, text_lower)
        if match:
            return int(float(match.group(1)) * multiplier), None

    # Try word-only patterns like "ek lakh", "do lakh"
    word_numbers = {
        "ek": 1, "do": 2, "teen": 3, "char": 4, "paanch": 5,
        "छह": 6, "saat": 7, "aath": 8, "nau": 9, "das": 10,
        "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पांच": 5,
    }
    for word, num in word_numbers.items():
        for unit_word, multiplier in INCOME_WORDS.items():
            if unit_word in ["lakh", "लाख", "lac", "हजार", "hajar", "हज़ार", "हज़ार"]:
                pattern = rf'{re.escape(word)}\s*{re.escape(unit_word)}'
                if re.search(pattern, text_lower):
                    return int(num * multiplier), None

    # Check for monthly income (multiply by 12)
    monthly_pattern = rf'(\d+(?:\.\d+)?)\s*(?:per month|monthly|महीने|महीना|प्रति महीना|प्रतिमाह)'
    monthly_match = re.search(monthly_pattern, text_lower)
    if monthly_match:
        monthly = float(monthly_match.group(1))
        return int(monthly * 12), None

    # Check for yearly income with plain number (e.g., "varshik 80000", "80000 saal", "50 hazar saal")
    yearly_indicators = ["varshik", "utpanna", "annual", "per year", "saal", "वार्षिक", "वर्षिक", "सालाना"]
    # Also look for income-related words that suggest this is an income figure
    income_context_words = ["aamdani", "utpanna", "income", "aamdani", "kamai", "earning", "salary", "pension"]

    best_match = None
    best_score = -1

    for indicator in yearly_indicators:
        # Find ALL occurrences of this indicator
        start = 0
        while True:
            idx = text_lower.find(indicator, start)
            if idx == -1:
                break

            # Score this occurrence based on nearby income context words
            context_start = max(0, idx - 50)
            context_end = min(len(text_lower), idx + len(indicator) + 50)
            context = text_lower[context_start:context_end]

            score = 0
            # Bonus for income context words nearby
            for w in income_context_words:
                if w in context:
                    score += 10
            # Bonus for number words (hazar/lakh/crore) nearby
            if any(re.search(rf'\b{re.escape(w)}\b', context) for w in ["hazar", "hajar", "हजार", "हज़ार", "thousand", "lakh", "लाख", "lac", "crore", "करोड", "करोड़", "कोटी"]):
                score += 20

            # Look for number AFTER the indicator
            after_start = idx + len(indicator)
            after_end = min(len(text_lower), after_start + 50)
            after_text = text_lower[after_start:after_end]
            nums = re.findall(r'\d+(?:\.\d+)?', after_text)

            # Also look for number BEFORE the indicator
            before_start = max(0, idx - 30)
            before_text = text_lower[before_start:idx]
            nums_before = re.findall(r'\d+(?:\.\d+)?', before_text)

            # Prefer number AFTER, then before
            candidate_num = None
            candidate_multiplier = 1
            candidate_context = context

            if nums:
                candidate_num = float(nums[0])
                # Check for multiplier in AFTER text
                if any(re.search(rf'\b{re.escape(w)}\b', after_text) for w in ["hazar", "hajar", "हजार", "हज़ार", "thousand"]):
                    candidate_multiplier = 1000
                elif any(re.search(rf'\b{re.escape(w)}\b', after_text) for w in ["lakh", "लाख", "lac"]):
                    candidate_multiplier = 100000
                elif any(re.search(rf'\b{re.escape(w)}\b', after_text) for w in ["crore", "करोड", "करोड़", "कोटी"]):
                    candidate_multiplier = 10000000
                candidate_context = after_text
            elif nums_before:
                candidate_num = float(nums_before[-1])
                # Check for multiplier in BEFORE text
                if any(re.search(rf'\b{re.escape(w)}\b', before_text) for w in ["hazar", "hajar", "हजार", "हज़ार", "thousand"]):
                    candidate_multiplier = 1000
                elif any(re.search(rf'\b{re.escape(w)}\b', before_text) for w in ["lakh", "लाख", "lac"]):
                    candidate_multiplier = 100000
                elif any(re.search(rf'\b{re.escape(w)}\b', before_text) for w in ["crore", "करोड", "करोड़", "कोटी"]):
                    candidate_multiplier = 10000000
                candidate_context = before_text

            if candidate_num is not None:
                # Boost score if multiplier found
                if candidate_multiplier > 1:
                    score += 30
                if score > best_score:
                    best_score = score
                    best_match = (int(candidate_num * candidate_multiplier), candidate_context)

            start = idx + 1

    if best_match:
        return best_match[0], None

    # Check for daily/irregular income patterns - return as note
    daily_pattern = rf'(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*(?:per day|daily|रोज|दिन|प्रति दिन)'
    daily_match = re.search(daily_pattern, text_lower)
    if daily_match:
        low = float(daily_match.group(1))
        high = float(daily_match.group(2))
        # Return None for annual_income, store note
        return None, f"{low}-{high} per day"

    # Single daily amount
    single_daily = rf'(\d+(?:\.\d+)?)\s*(?:per day|daily|रोज|दिन|प्रति दिन)'
    single_match = re.search(single_daily, text_lower)
    if single_match:
        daily = float(single_match.group(1))
        return None, f"{daily} per day"

    # No clear income pattern found - return None
    # Don't guess by picking the first number in text (could be age, land acres, etc.)
    return None, None


def _normalize_occupation(text: str) -> Optional[str]:
    """Normalize occupation to standard English."""
    text_lower = text.lower()
    for key, value in OCCUPATION_MAP.items():
        if key in text_lower:
            return value
    return None


def _infer_state_from_text(text: str) -> Optional[str]:
    """Infer state from district/city mentioned in text."""
    text_lower = text.lower()
    for district, state in DISTRICT_TO_STATE.items():
        if district in text_lower:
            return state
    return None


def _normalize_state(text: str) -> Optional[str]:
    """Normalize state to standard English."""
    # First try direct state mention
    text_lower = text.lower()
    for key, value in STATE_MAP.items():
        if key in text_lower:
            return value
    # Then infer from district/city
    return _infer_state_from_text(text)


def _normalize_district(text: str) -> Optional[str]:
    """Normalize district to standard English."""
    text_lower = text.lower()
    for key, value in DISTRICT_MAP.items():
        if key in text_lower:
            return value
    return None


def _infer_gender_from_text(text: str) -> Optional[str]:
    """Infer gender from grammar and vocabulary."""
    text_lower = text.lower()

    # Check female indicators
    for indicator in FEMALE_INDICATORS:
        if indicator in text_lower:
            return "female"

    # Check male indicators
    for indicator in MALE_INDICATORS:
        if indicator in text_lower:
            return "male"

    # No clear signal
    return None


def _normalize_gender(text: str) -> Optional[str]:
    """Normalize gender to standard English."""
    # First try explicit words
    text_lower = text.lower()
    for key, value in GENDER_MAP.items():
        if key in text_lower:
            return value
    # Then infer from grammar/vocabulary
    return _infer_gender_from_text(text)


def _normalize_caste(text: str) -> Optional[str]:
    """Normalize caste category to standard English."""
    import re
    text_lower = text.lower()
    for key, value in CASTE_MAP.items():
        # Use word boundaries for short keys to avoid false positives (e.g., "st" in "street")
        if len(key) <= 4:
            pattern = rf'\b{re.escape(key)}\b'
            if re.search(pattern, text_lower):
                return value
        else:
            if key in text_lower:
                return value
    return None


def _detect_lpg_status(text: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """Detect LPG-related keywords in text and set has_lpg accordingly."""
    text_lower = text.lower()

    # LPG-related keywords indicating NO LPG connection
    lpg_negative_keywords = [
        "gas connection nahi", "gas nahi", "no lpg", "no lpg connection",
        "गॅस नाही", "गैस नाही", "गॅस कनेक्शन नाही", "गैस कनेक्शन नहीं",
        "एलपीजी नाही", "lpg nahi", "lpg connection nahi"
    ]

    has_lpg = None
    for keyword in lpg_negative_keywords:
        if keyword in text.lower():
            has_lpg = False
            break

    if has_lpg is not None:
        profile_data["has_lpg"] = has_lpg

    return profile_data


def extract_profile(text: str, debug: bool = False) -> Tuple[Profile, List[str]]:
    """
    Extract user profile from free text input using LLM.

    Args:
        text: User text in any Indian language or Hinglish
        debug: If True, print raw LLM JSON output for debugging

    Returns:
        Tuple of (Profile object, list of missing important fields)
    """
    system_prompt = """You are a profile extractor for a government scheme eligibility system.
Extract structured information from the user's text. The user may write in Hindi, Marathi, English, or mixed (including Hinglish/Latin script for Indian languages).

Return ONLY valid JSON with these fields (use null if not mentioned):
- occupation: string (normalize to English: farmer, trader, business_owner, employee, student, homemaker, laborer, driver, street_vendor, entrepreneur)
- age: integer or null
- gender: string (normalize to English: male, female) or null if unclear
- state: string (normalize to English state name) or null
- district: string (normalize to English district name) or null
- annual_income: integer (INR per year) or null
- income_note: string or null (original phrase if daily/irregular income given)
- land_acres: number (float) or null
- caste_category: string (normalize to English: General, SC, ST, OBC, EWS) or null
- family_members: integer or null

Rules:
- NEVER guess. Use null if information is not present.
- GENDER: Infer from grammar/words. Feminine forms (चलती हूं, करती हूं, रहती हूं, करती हूँ, राहते, चालते, woman, widow, vidhwa, mahila, patni, beti, ladki) → female. Masculine forms (चलता हूं, करता हूं, विधुर) → male. If no clear signal → null.
- STATE: If district/city mentioned (Wardha, Nagpur, Pune, Nashik, Mumbai, Ahmedabad, etc.), fill the correct state in English. If no place named → null.
- INCOME: Only fill annual_income if annual or monthly figure given (monthly × 12). If daily/irregular range (e.g., "500-700 per day"), set annual_income: null and income_note: "500-700 per day".
- Convert income words (lakh, hajar, हजार, लाख) to actual numbers.
- Normalize all categorical values to standard English terms.
- If user says "80 hajar" or "८० हजार" → annual_income: 80000
- If user says "2 acre" → land_acres: 2.0
- Occupation, state, district, gender, caste must be in English in the output.

Examples:

Example 1:
Input: "Mi shetkari aahe, Wardha madhe. 2 acre jamin. Varshik utpanna 80000. Vaya 45 varsh. Mulga mulgi 2."
Output: {"occupation": "farmer", "age": 45, "gender": "male", "state": "Maharashtra", "district": "Wardha", "annual_income": 80000, "income_note": null, "land_acres": 2.0, "caste_category": null, "family_members": 2}

Example 2:
Input: "Main Mumbai mein apna chota sa business chalti hoon. Beauty parlor hai. Varshik aamdani 3 lakh. Age 32. SC category."
Output: {"occupation": "business_owner", "age": 32, "gender": "female", "state": "Maharashtra", "district": "Mumbai", "annual_income": 300000, "income_note": null, "land_acres": null, "caste_category": "SC", "family_members": null}

Example 3:
Input: "Mi Nashik madhe street vendor aahe. Veg-bhaji vikto. Rozache 500-700 milte. Vaya 40."
Output: {"occupation": "street_vendor", "age": 40, "gender": "male", "state": "Maharashtra", "district": "Nashik", "annual_income": null, "income_note": "500-700 per day", "land_acres": null, "caste_category": null, "family_members": null}"""

    user_prompt = f"Extract profile from this text: {text}"

    try:
        # Use temperature=0 for deterministic extraction
        result = call_json(system_prompt, user_prompt, max_tokens=800, temperature=0.0)
    except Exception as e:
        # Fallback: try to extract with regex patterns if LLM fails
        return _fallback_extract(text)

    # DEBUG: Print raw LLM JSON
    if debug:
        print(f"\n=== RAW LLM JSON OUTPUT ===")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print(f"=== END RAW LLM JSON ===\n")

    # Use LLM's extracted values as base, then apply post-checks
    llm_annual_income = result.get("annual_income")
    llm_income_note = result.get("income_note")

    # Convert LLM's annual_income to int if it's a number
    if llm_annual_income is not None:
        try:
            llm_annual_income = int(float(str(llm_annual_income)))
        except (ValueError, TypeError):
            llm_annual_income = None

    profile_data = {
        "occupation": _normalize_occupation(result.get("occupation", "")) if result.get("occupation") else None,
        "age": result.get("age") if isinstance(result.get("age"), int) else (_extract_number(str(result.get("age", ""))) or None),
        "gender": _normalize_gender(result.get("gender", "")) if result.get("gender") else None,
        "state": _normalize_state(result.get("state", "")) if result.get("state") else None,
        "district": _normalize_district(result.get("district", "")) if result.get("district") else None,
        "annual_income": llm_annual_income,
        "income_note": llm_income_note,
        "land_acres": float(result.get("land_acres")) if result.get("land_acres") is not None else None,
        "caste_category": _normalize_caste(result.get("caste_category", "")) if result.get("caste_category") else None,
        "family_members": result.get("family_members") if isinstance(result.get("family_members"), int) else (_extract_number(str(result.get("family_members", ""))) or None),
    }

    # Apply deterministic post-processing (gender, income)
    profile_data = _apply_post_processing(text, profile_data)

    # Detect LPG-related keywords and set has_lpg
    profile_data = _detect_lpg_status(text, profile_data)

    # Compute missing_fields from null fields in Python (not from LLM)
    missing_fields = _compute_missing_fields(profile_data)

    profile = Profile(**profile_data)
    return profile, missing_fields


def _fallback_extract(text: str) -> Tuple[Profile, List[str]]:
    """Fallback extraction using regex patterns when LLM is unavailable."""
    text_lower = text.lower()

    # Extract income with note
    annual_income, income_note = _parse_income(text)

    # Extract age
    age_match = re.search(r'(?:age|vaya|उमर|उम्र|आयु|वय)\s*(?:hai| आहे|है|:)?\s*(\d+)', text_lower)
    age = int(age_match.group(1)) if age_match else _extract_number(text)

    # Extract gender
    gender = _normalize_gender(text)

    # Extract state
    state = _normalize_state(text)

    # Extract district
    district = _normalize_district(text)

    # Extract occupation
    occupation = _normalize_occupation(text)

    # Extract land acres
    land_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:acre|एकड|एकड़)', text_lower)
    land_acres = float(land_match.group(1)) if land_match else None

    # Extract caste
    caste = _normalize_caste(text)

    # Extract family members
    family_match = re.search(r'(?:family|परिवार|कुटुंब)\s*(?:members|सदस्य|अंग)?\s*(\d+)', text_lower)
    family_members = int(family_match.group(1)) if family_match else None

    profile_data = {
        "occupation": occupation,
        "age": int(age) if age else None,
        "gender": gender,
        "state": state,
        "district": district,
        "annual_income": annual_income,
        "income_note": income_note,
        "land_acres": land_acres,
        "caste_category": caste,
        "family_members": family_members,
    }

    # Apply deterministic post-processing (gender, income)
    profile_data = _apply_post_processing(text, profile_data)

    # Compute missing_fields from null fields in Python (not from LLM)
    missing_fields = _compute_missing_fields(profile_data)

    return Profile(**profile_data), missing_fields