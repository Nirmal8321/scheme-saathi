"""Test for select_results function - no LLM required."""
import json
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.explain import select_results
from backend.schemas import SchemeResult


def build_widow_mock_results():
    """Build mock SchemeResults for elderly widow profile (sample-5)."""
    return [
        # pm_ujjwala
        SchemeResult(scheme_id="pm_ujjwala", scheme="PM Ujjwala Yojana", eligible="maybe",
                    reason="Needs verification: bpl_status", benefit="...", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        SchemeResult(scheme_id="pmjay", scheme="Ayushman Bharat PM-JAY", eligible="maybe",
                    reason="Needs verification: secc_listing_or_income_proof", benefit="...", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        SchemeResult(scheme_id="pm_awas", scheme="PM Awas Yojana", eligible="maybe",
                    reason="Needs verification: house_ownership", benefit="...", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        SchemeResult(scheme_id="pm_svanidhi", scheme="PM SVANidhi", eligible="maybe",
                    reason="Needs verification: vending_certificate", benefit="...", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        SchemeResult(scheme_id="ladki_bahin", scheme="Ladki Bahin", eligible="maybe",
                    reason="Needs verification: family_income_proof", benefit="...", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        # namo_shetkari - needs farmer occupation
        SchemeResult(scheme_id="namo_shetkari", scheme="Namo Shetkari Mahasanman Nidhi", eligible="no",
                    reason="occupation 'None' not in allowed list ['farmer', 'agriculturist']", benefit="...", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        # pm_kisan - needs farmer occupation
        SchemeResult(scheme_id="pm_kisan", scheme="PM-KISAN", eligible="no",
                    reason="occupation 'None' not in allowed list ['farmer', 'agriculturist']", benefit="...", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        # mudra_loan
        SchemeResult(scheme_id="mudra_loan", scheme="Mudra Loan", eligible="maybe",
                    reason="occupation 'None' not in allowed list ['entrepreneur', 'business_owner', 'self_employed', 'trader', 'manufacturer', 'service_provider', 'street_vendor', 'shopkeeper', 'artisan', 'small_business']", benefit="...", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        # stand_up_india
        SchemeResult(scheme_id="stand_up_india", scheme="Stand-Up India", eligible="no",
                    reason="occupation 'None' not in allowed list ['entrepreneur', 'business_owner']", benefit="...", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        # post_matric_scholarship
        SchemeResult(scheme_id="post_matric_scholarship", scheme="Post-Matric Scholarship", eligible="maybe",
                    reason="occupation 'None' not in allowed list ['student']", benefit="...", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
    ]


def build_farmer_mock_results():
    """Build mock SchemeResults for Wardha farmer profile (sample-1)."""
    return [
        # pm_kisan - YES for farmer with land
        SchemeResult(scheme_id="pm_kisan", scheme="PM-KISAN", eligible="yes",
                    reason="Eligible: farmer with land", benefit="...", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        # namo_shetkari - YES for Maharashtra farmer
        SchemeResult(scheme_id="namo_shetkari", scheme="Namo Shetkari Mahasanman Nidhi", eligible="yes",
                    reason="Eligible: Maharashtra farmer with land", benefit="...", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        # pm_ujjwala - NO (has LPG)
        SchemeResult(scheme_id="pm_ujjwala", scheme="PM Ujjwala Yojana", eligible="no",
                    reason="already has an LPG connection", benefit="...", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        # pmjay - maybe (needs SECC verification)
        SchemeResult(scheme_id="pmjay", scheme="Ayushman Bharat PM-JAY", eligible="maybe",
                    reason="Needs verification: secc_listing_or_income_proof", benefit="...", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        # pm_awas - maybe (needs house ownership verification)
        SchemeResult(scheme_id="pm_awas", scheme="PM Awas Yojana", eligible="maybe",
                    reason="Needs verification: house_ownership", benefit="...", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        # pm_svanidhi - maybe (needs vending certificate)
        SchemeResult(scheme_id="pm_svanidhi", scheme="PM SVANidhi", eligible="maybe",
                    reason="Needs verification: vending_certificate", benefit="...", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        # ladki_bahin - NO (not female)
        SchemeResult(scheme_id="ladki_bahin", scheme="Ladki Bahin", eligible="no",
                    reason="gender 'male' does not match required 'female'", benefit="...", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        # mudra_loan - maybe (needs occupation verification)
        SchemeResult(scheme_id="mudra_loan", scheme="Mudra Loan", eligible="maybe",
                    reason="occupation 'farmer' not in allowed list ['entrepreneur', 'business_owner', 'self_employed', 'trader', 'manufacturer', 'service_provider', 'street_vendor', 'shopkeeper', 'artisan', 'small_business']", benefit="...", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        # stand_up_india - NO (not SC/ST/woman)
        SchemeResult(scheme_id="stand_up_india", scheme="Stand-Up India", eligible="no",
                    reason="gender 'male' does not match required", benefit="...", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        # post_matric_scholarship - NO (not student)
        SchemeResult(scheme_id="post_matric_scholarship", scheme="Post-Matric Scholarship", eligible="no",
                    reason="occupation 'farmer' not in allowed list ['student']", benefit="...", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
    ]


def test_widow_profile():
    """Test select_results with elderly widow profile (sample-5)."""
    from backend.explain import select_results

    # Widow profile: age 68, female, income 50000, occupation null, has_lpg false
    profile = {
        "occupation": None,
        "age": 68,
        "gender": "female",
        "state": None,
        "district": None,
        "annual_income": 50000,
        "land_acres": None,
        "caste_category": None,
        "family_members": None,
        "has_lpg": False
    }

    results = build_widow_mock_results()
    selected = select_results(results, profile)

    selected_ids = [r.scheme_id for r in selected]
    print("Widow profile - Selected:", selected_ids)
    for r in selected:
        print(f"  {r.scheme_id} ({r.eligible}): {r.reason}")

    # Assertions
    assert selected_ids == ["pm_ujjwala", "pmjay", "pm_awas"], f"Expected ['pm_ujjwala', 'pmjay', 'pm_awas'], got {selected_ids}"
    assert "pm_svanidhi" not in selected_ids
    assert "namo_shetkari" not in selected_ids
    assert "pm_kisan" not in selected_ids
    assert "ladki_bahin" not in selected_ids
    assert "mudra_loan" not in selected_ids
    assert "stand_up_india" not in selected_ids
    assert "post_matric_scholarship" not in selected_ids

    # Check order: pm_ujjwala first (female, no LPG)
    assert selected[0].scheme_id == "pm_ujjwala"
    print("✓ Widow profile test passed!")


def test_farmer_profile():
    """Test select_results with Wardha farmer profile (sample-1)."""
    from backend.explain import select_results

    # Farmer profile: occupation=farmer, age=45, gender=male, state=Maharashtra, income=80000, land=2
    profile = {
        "occupation": "farmer",
        "age": 45,
        "gender": "male",
        "state": "Maharashtra",
        "district": "Wardha",
        "annual_income": 80000,
        "land_acres": 2.0,
        "caste_category": None,
        "family_members": 2,
        "has_lpg": True
    }

    results = build_farmer_mock_results()
    selected = select_results(results, profile)

    selected_ids = [r.scheme_id for r in selected]
    print("Farmer profile - Selected:", selected_ids)
    for r in selected:
        print(f"  {r.scheme_id} ({r.eligible}): {r.reason}")

    # pm_kisan and namo_shetkari should be "yes" and come first
    assert selected_ids[0] == "pm_kisan", f"First should be pm_kisan, got {selected_ids[0]}"
    assert selected_ids[1] == "namo_shetkari", f"Second should be namo_shetkari, got {selected_ids[1]}"
    assert selected_ids[0:2] == ["pm_kisan", "namo_shetkari"]
    print("✓ Farmer profile test passed!")


def test_no_caste_in_reasons():
    """Assert no explanation contains 'जाति' or 'caste' unless scheme has categories in rules."""
    from backend.explain import select_results

    # Use widow profile
    profile = {
        "occupation": None, "age": 68, "gender": "female", "state": None,
        "district": None, "annual_income": 50000, "land_acres": None,
        "caste_category": None, "family_members": None, "has_lpg": False
    }

    results = build_widow_mock_results()
    selected = select_results(results, profile)

    for r in selected:
        assert "जाति" not in r.reason, f"Reason contains 'जाति': {r.reason}"
        assert "caste" not in r.reason.lower(), f"Reason contains 'caste': {r.reason}"

    print("✓ No caste mentions in reasons!")


if __name__ == "__main__":
    print("=" * 60)
    print("Running test_select.py")
    print("=" * 60)
    
    test_widow_profile()
    print()
    test_farmer_profile()
    print()
    test_no_caste_in_reasons()
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)