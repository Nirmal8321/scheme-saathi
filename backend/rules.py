"""Rule checking engine for scheme eligibility."""
from typing import Dict, Any, List, Tuple, Optional


def check_rules(profile: Dict[str, Any], scheme: Dict[str, Any]) -> Tuple[str, List[str], List[str]]:
    """
    Check scheme rules against a user profile.

    Args:
        profile: User profile dict with keys like age, gender, annual_income,
                 state, occupation, caste_category, land_acres
        scheme: Scheme dict from schemes.json with "rules" object

    Returns:
        Tuple of (verdict, reasons, missing_fields)
        - verdict: "yes", "no", or "maybe"
        - reasons: List of short reason strings for "no" verdicts
        - missing_fields: List of profile fields that are null but needed for a rule
    """
    rules = scheme.get("rules", {})
    reasons = []
    missing_fields = []
    has_known_failure = False

    # Helper to get profile value
    def get_profile_value(key: str) -> Any:
        return profile.get(key)

    # 1. Age checks
    min_age = rules.get("min_age")
    max_age = rules.get("max_age")
    age = get_profile_value("age")

    if min_age is not None:
        if age is not None:
            if age < min_age:
                reasons.append(f"age {age} below minimum {min_age}")
                has_known_failure = True
        else:
            missing_fields.append("age")

    if max_age is not None:
        if age is not None:
            if age > max_age:
                reasons.append(f"age {age} above maximum {max_age}")
                has_known_failure = True
        else:
            missing_fields.append("age")

    # 2. Gender check
    required_gender = rules.get("gender")
    gender = get_profile_value("gender")

    if required_gender is not None:
        if gender is not None:
            if gender.lower() != required_gender.lower():
                reasons.append(f"gender '{gender}' does not match required '{required_gender}'")
                has_known_failure = True
        else:
            missing_fields.append("gender")

    # 3. Income check (max_income)
    max_income = rules.get("max_income")
    annual_income = get_profile_value("annual_income")

    if max_income is not None:
        if annual_income is not None:
            if annual_income > max_income:
                reasons.append(f"annual income ₹{annual_income:,} exceeds limit ₹{max_income:,}")
                has_known_failure = True
        else:
            missing_fields.append("annual_income")

    # 4. State check
    allowed_states = rules.get("states", [])
    state = get_profile_value("state")

    if allowed_states:
        if state is not None:
            if state not in allowed_states:
                reasons.append(f"state '{state}' not in allowed states {allowed_states}")
                has_known_failure = True
        else:
            missing_fields.append("state")

    # 5. Occupation check
    allowed_occupations = rules.get("occupations", [])
    occupation = get_profile_value("occupation")

    if allowed_occupations:
        if occupation is not None:
            if occupation not in allowed_occupations:
                reasons.append(f"occupation '{occupation}' not in allowed list {allowed_occupations}")
                has_known_failure = True
        else:
            missing_fields.append("occupation")

    # 6. Land check
    needs_land = rules.get("needs_land", False)
    land_acres = get_profile_value("land_acres")

    if needs_land:
        if land_acres is not None:
            if land_acres <= 0:
                reasons.append("no cultivable land")
                has_known_failure = True
        else:
            missing_fields.append("land_acres")

    # 7. Caste category check
    allowed_categories = rules.get("categories", [])
    caste_category = get_profile_value("caste_category")

    if allowed_categories:
        if caste_category is not None:
            if caste_category not in allowed_categories:
                reasons.append(f"caste category '{caste_category}' not in allowed list {allowed_categories}")
                has_known_failure = True
        else:
            missing_fields.append("caste_category")

    # Determine verdict
    if has_known_failure:
        verdict = "no"
    elif missing_fields:
        verdict = "maybe"
    else:
        verdict = "yes"

    # Handle requires_verification: if verdict is "yes" but verification needed, downgrade to "maybe"
    if verdict == "yes":
        requires_verification = scheme.get("requires_verification", [])
        if requires_verification:
            verdict = "maybe"
            for item in requires_verification:
                reasons.append(f"Needs verification: {item.replace('_', ' ')}")

    return verdict, reasons, missing_fields


def check_all_schemes(profile: Dict[str, Any], schemes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Check all schemes against a profile.

    Returns list of dicts with scheme_id, verdict, reasons, missing_fields.
    """
    results = []
    for scheme in schemes:
        verdict, reasons, missing = check_rules(profile, scheme)
        results.append({
            "scheme_id": scheme["id"],
            "scheme_name": scheme["name"],
            "verdict": verdict,
            "reasons": reasons,
            "missing_fields": missing,
        })
    return results