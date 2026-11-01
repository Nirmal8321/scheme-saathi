#!/usr/bin/env python3
"""No-LLM tests for rules.py - fix income check regression."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.rules import check_rules


def load_schemes():
    import json
    base_dir = Path(__file__).parent.parent
    with open(base_dir / "data" / "schemes.json", "r", encoding="utf-8") as f:
        return json.load(f)


SCHEMES = load_schemes()
SCHEME_MAP = {s["id"]: s for s in SCHEMES}


def test_post_matric_income_exceeds():
    """Student with income 300000 > 250000 must get 'no' verdict."""
    profile = {
        "age": 22,
        "caste_category": "SC",
        "gender": "male",
        "annual_income": 300000,
        "state": "Delhi",
        "occupation": "student",
        "land_acres": 0,
    }
    scheme = SCHEME_MAP["post_matric_scholarship"]
    verdict, reasons, missing = check_rules(profile, scheme)
    print(f"Test 1 - Income 300000: verdict={verdict}, reasons={reasons}, missing={missing}")
    assert verdict == "no", f"Expected 'no', got '{verdict}'"
    assert any("exceeds limit" in r and "250" in r for r in reasons), f"Expected income exceed reason, got {reasons}"
    print("✓ Test 1 passed: Income 300000 → 'no' with 'exceeds limit 250000'")


def test_post_matric_income_within_limit():
    """Student with income 200000 ≤ 250000 must get 'maybe' (due to requires_verification)."""
    profile = {
        "age": 22,
        "caste_category": "SC",
        "gender": "male",
        "annual_income": 200000,
        "state": "Delhi",
        "occupation": "student",
        "land_acres": 0,
    }
    scheme = SCHEME_MAP["post_matric_scholarship"]
    verdict, reasons, missing = check_rules(profile, scheme)
    print(f"Test 2 - Income 200000: verdict={verdict}, reasons={reasons}, missing={missing}")
    assert verdict == "maybe", f"Expected 'maybe', got '{verdict}'"
    assert any("Needs verification: income certificate" in r for r in reasons), f"Expected verification reason, got {reasons}"
    print("✓ Test 2 passed: Income 200000 → 'maybe' with 'Needs verification: income certificate'")


def test_requires_verification_never_yes():
    """Schemes with requires_verification must never return 'yes'."""
    # Test post_matric_scholarship
    profile = {
        "age": 22,
        "caste_category": "SC",
        "gender": "male",
        "annual_income": 200000,
        "state": "Delhi",
        "occupation": "student",
        "land_acres": 0,
    }
    scheme = SCHEME_MAP["post_matric_scholarship"]
    verdict, _, _ = check_rules(profile, scheme)
    assert verdict != "yes", f"post_matric_scholarship must not return 'yes', got '{verdict}'"

    # Test pmjay
    scheme = SCHEME_MAP["pmjay"]
    verdict, _, _ = check_rules({"age": 30, "annual_income": 100000, "occupation": "worker", "gender": "male", "state": "Delhi"}, scheme)
    assert verdict != "yes", f"pmjay must not return 'yes', got '{verdict}'"

    # Test pm_awas
    scheme = SCHEME_MAP["pm_awas"]
    verdict, _, _ = check_rules({"age": 30, "annual_income": 100000, "occupation": "worker", "gender": "female", "state": "Delhi", "land_acres": 100}, scheme)
    assert verdict != "yes", f"pm_awas must not return 'yes', got '{verdict}'"

    # Test pm_ujjwala
    scheme = SCHEME_MAP["pm_ujjwala"]
    verdict, _, _ = check_rules({"age": 30, "annual_income": 100000, "gender": "female", "state": "Delhi", "has_lpg": False}, scheme)
    assert verdict != "yes", f"pm_ujjwala must not return 'yes', got '{verdict}'"

    print("✓ Test 3 passed: requires_verification schemes never return 'yes'")


def test_farmer_wardha_pm_kisan():
    """Farmer in Wardha should get pm_kisan 'yes'."""
    profile = {
        "age": 42,
        "caste_category": "General",
        "gender": "male",
        "annual_income": 120000,
        "state": "Maharashtra",
        "occupation": "farmer",
        "land_acres": 3,
    }
    scheme = SCHEME_MAP["pm_kisan"]
    verdict, reasons, missing = check_rules(profile, scheme)
    print(f"Test 4 - Farmer Wardha: verdict={verdict}, reasons={reasons}, missing={missing}")
    assert verdict == "yes", f"Expected 'yes', got '{verdict}'"
    print("✓ Test 4 passed: Farmer Wardha → pm_kisan 'yes'")


def test_widow_ladki_bahin():
    """Widow age 68 should get ladki_bahin 'no' (age > 65)."""
    profile = {
        "age": 68,
        "caste_category": "General",
        "gender": "female",
        "annual_income": 50000,
        "state": "Maharashtra",
        "occupation": None,
        "land_acres": 0,
    }
    scheme = SCHEME_MAP["ladki_bahin"]
    verdict, reasons, missing = check_rules(profile, scheme)
    print(f"Test 5 - Widow age 68: verdict={verdict}, reasons={reasons}, missing={missing}")
    assert verdict == "no", f"Expected 'no', got '{verdict}'"
    assert any("above maximum 65" in r for r in reasons), f"Expected age exceed reason, got {reasons}"
    print("✓ Test 5 passed: Widow age 68 → ladki_bahin 'no'")


def test_schemes_json_unchanged():
    """Verify schemes.json still has all required fields for all schemes."""
    import json
    base_dir = Path(__file__).parent.parent
    with open(base_dir / "data" / "schemes.json", "r", encoding="utf-8") as f:
        schemes = json.load(f)

    for s in schemes:
        assert "rules" in s, f"Scheme {s['id']} missing 'rules'"
        assert "requires_verification" in s, f"Scheme {s['id']} missing 'requires_verification'"
        rules = s["rules"]
        assert "max_income" in rules, f"Scheme {s['id']} rules missing max_income"
        assert "occupations" in rules, f"Scheme {s['id']} rules missing occupations"
        assert "requires_verification" in s, f"Scheme {s['id']} missing requires_verification"

    print("✓ Test 6 passed: All schemes have required fields in schemes.json")


if __name__ == "__main__":
    print("Running rules tests...")
    print("=" * 50)
    test_post_matric_income_exceeds()
    test_post_matric_income_within_limit()
    test_requires_verification_never_yes()
    test_farmer_wardha_pm_kisan()
    test_widow_ladki_bahin()
    test_schemes_json_unchanged()
    print("=" * 50)
    print("All tests passed!")