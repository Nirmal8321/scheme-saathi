#!/usr/bin/env python3
"""No-LLM test for select_results keyword boosting."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.explain import select_results
from backend.schemas import SchemeResult


def test_crop_insurance_seeds_keywords():
    """Test that 'farmer, crop insurance and seeds' boosts pmfby and seed_subsidy."""
    # Create mock results for a farmer profile
    profile = {
        "gender": "male",
        "age": 42,
        "annual_income": 120000,
        "state": "Maharashtra",
        "occupation": "farmer",
        "land_acres": 3,
        "caste_category": "General"
    }

    # Query text with keywords
    query_text = "farmer, crop insurance and seeds"

    # Create mock SchemeResult objects (simulating what match_schemes would return)
    results = [
        SchemeResult(
            scheme_id="pm_kisan",
            scheme="PM-KISAN",
            eligible="yes",
            reason="Rule check passed",
            benefit="Rs 6,000 per year in 3 installments",
            documents=["Aadhaar", "7/12 land record"],
            how_to_apply="pmkisan.gov.in",
            official_link="https://pmkisan.gov.in",
            source_quote="",
            explanation="",
        ),
        SchemeResult(
            scheme_id="pmfby",
            scheme="Pradhan Mantri Fasal Bima Yojana (PMFBY)",
            eligible="yes",
            reason="Rule check passed",
            benefit="Crop insurance: Sum insured per hectare",
            documents=["Aadhaar", "Land records"],
            how_to_apply="pmfby.gov.in",
            official_link="https://pmfby.gov.in",
            source_quote="",
            explanation="",
        ),
        SchemeResult(
            scheme_id="seed_subsidy",
            scheme="Maharashtra Beej Unnati Yojana (Seed Subsidy)",
            eligible="yes",
            reason="Rule check passed",
            benefit="Subsidy on certified seeds: 50% for general farmers",
            documents=["Aadhaar", "7/12 extract"],
            how_to_apply="mahadbt.maharashtra.gov.in",
            official_link="https://mahadbt.maharashtra.gov.in",
            source_quote="",
            explanation="",
        ),
        SchemeResult(
            scheme_id="kcc",
            scheme="Kisan Credit Card (KCC)",
            eligible="maybe",
            reason="Needs verification: land cultivation or tenancy",
            benefit="Revolving credit up to Rs 3 lakh",
            documents=["Aadhaar", "Land records"],
            how_to_apply="Bank branch",
            official_link="https://agricoop.gov.in",
            source_quote="",
            explanation="",
        ),
        SchemeResult(
            scheme_id="mudra_loan",
            scheme="Mudra Loan (PM Mudra Yojana)",
            eligible="no",
            reason="Occupation 'farmer' not in allowed list",
            benefit="Up to Rs 10 lakh loan",
            documents=["Aadhaar", "PAN"],
            how_to_apply="Bank branch",
            official_link="https://mudra.org.in",
            source_quote="",
            explanation="",
        ),
    ]

    # Call select_results with query text
    selected = select_results(results, profile, query_text)

    # Extract scheme IDs in order
    selected_ids = [r.scheme_id for r in selected]
    print(f"Selected scheme IDs (in order): {selected_ids}")

    # Assertions
    assert "pmfby" in selected_ids, "pmfby should be selected"
    assert "seed_subsidy" in selected_ids, "seed_subsidy should be selected"

    # pmfby should be in top 3 (ranked higher due to insurance keyword)
    pmfby_index = selected_ids.index("pmfby")
    assert pmfby_index < 3, f"pmfby should be in top 3, got index {pmfby_index} (order: {selected_ids})"

    print("✓ All tests passed!")
    print(f"  Final order: {selected_ids}")


def test_loan_keywords():
    """Test that 'loan' keyword boosts credit_finance schemes."""
    profile = {
        "gender": "male",
        "age": 35,
        "annual_income": 250000,
        "state": "Karnataka",
        "occupation": "business_owner",
        "land_acres": 0,
        "caste_category": "General"
    }

    query_text = "need a loan for business"

    results = [
        SchemeResult(
            scheme_id="mudra_loan",
            scheme="Mudra Loan (PM Mudra Yojana)",
            eligible="yes",
            reason="Rule check passed",
            benefit="Up to Rs 10 lakh loan",
            documents=["Aadhaar", "PAN"],
            how_to_apply="mudra.org.in",
            official_link="https://mudra.org.in",
            source_quote="",
            explanation="",
        ),
        SchemeResult(
            scheme_id="kcc",
            scheme="Kisan Credit Card (KCC)",
            eligible="no",
            reason="Occupation not farmer",
            benefit="Revolving credit up to Rs 3 lakh",
            documents=["Aadhaar", "Land records"],
            how_to_apply="Bank branch",
            official_link="https://agricoop.gov.in",
            source_quote="",
            explanation="",
        ),
        SchemeResult(
            scheme_id="stand_up_india",
            scheme="Stand-Up India",
            eligible="yes",
            reason="Rule check passed",
            benefit="Bank loan between Rs 10 lakh and Rs 1 crore",
            documents=["Aadhaar", "PAN"],
            how_to_apply="Bank branch",
            official_link="https://standupindia-scheme.com",
            source_quote="",
            explanation="",
        ),
    ]

    selected = select_results(results, profile, query_text)
    selected_ids = [r.scheme_id for r in selected]
    print(f"Loan test selected: {selected_ids}")

    # mudra_loan and stand_up_india should be ranked high (credit_finance category)
    assert "mudra_loan" in selected_ids, "mudra_loan should be selected"
    print("✓ Loan keyword test passed!")


if __name__ == "__main__":
    print("Testing keyword boosting in select_results...")
    print("=" * 50)
    test_crop_insurance_seeds_keywords()
    print()
    test_loan_keywords()
    print()
    print("All tests passed!")