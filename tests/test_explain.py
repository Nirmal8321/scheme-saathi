"""Test script for LLM #3 explainer functionality - 3 LLM calls only."""
import json
import sys
import os
import time
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.extract import extract_profile
from backend.match import match_schemes
from backend.explain import explain_results, select_results, answer_chat, explain_pdf
from backend.pdf_reader import extract_text
from backend.schemas import Profile


def load_sample_inputs() -> List[Dict[str, Any]]:
    """Load sample user inputs from JSON file."""
    with open(Path(__file__).parent / "sample_inputs.json", "r", encoding="utf-8") as f:
        return json.load(f)


def create_sample_pdf() -> bytes:
    """Create a simple sample PDF for testing if none exists."""
    try:
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Sample Government Scheme Notification\n\n")
        page.insert_text((50, 100), "Scheme: PM-KISAN\n")
        page.insert_text((50, 120), "Benefit: 6,000 रुपये per year in 3 installments\n")
        page.insert_text((50, 140), "Eligibility: Landholding farmer families with cultivable land\n")
        page.insert_text((50, 160), "Apply at: pmkisan.gov.in or nearest CSC center\n")
        page.insert_text((50, 180), "Deadline: Ongoing scheme, no deadline\n")
        page.insert_text((50, 200), "Contact: 155261 or pmkisan.gov.in\n")
        pdf_bytes = doc.tobytes()
        doc.close()
        return pdf_bytes
    except Exception:
        return b""


def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def test_select_results():
    """Test the select_results function (no LLM call)."""
    print_section("TESTING select_results (no LLM)")

    from backend.schemas import SchemeResult

    # Create a mock profile
    profile = {
        "occupation": "farmer",
        "age": 45,
        "gender": "male",
        "state": "Maharashtra",
        "annual_income": 80000,
        "land_acres": 2.0,
        "caste_category": None,
        "family_members": 2
    }

    # Create mock results with different verdicts
    results = [
        SchemeResult(scheme_id="pm_kisan", scheme="PM-KISAN", eligible="yes", reason="Eligible farmer", benefit="6,000 रुपये per year", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        SchemeResult(scheme_id="namo_shetkari", scheme="Namo Shetkari", eligible="yes", reason="Maharashtra farmer", benefit="6,000 रुपये per year", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        SchemeResult(scheme_id="pm_awas", scheme="PM Awas", eligible="maybe", reason="Needs verification: house ownership", benefit="", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        SchemeResult(scheme_id="pm_ujjwala", scheme="PM Ujjwala", eligible="maybe", reason="Needs verification: bpl status", benefit="", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        SchemeResult(scheme_id="ladki_bahin", scheme="Ladki Bahin", eligible="maybe", reason="missing caste_category", benefit="", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        SchemeResult(scheme_id="mudra_loan", scheme="Mudra Loan", eligible="maybe", reason="occupation unknown", benefit="", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        SchemeResult(scheme_id="pm_svanidhi", scheme="PM SVANidhi", eligible="maybe", reason="occupation unknown", benefit="", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        SchemeResult(scheme_id="stand_up_india", scheme="Stand Up India", eligible="no", reason="occupation not in allowed list", benefit="", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        SchemeResult(scheme_id="pm_awas", scheme="PM Awas", eligible="maybe", reason="Needs verification: house ownership", benefit="", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        SchemeResult(scheme_id="pm_ujjwala", scheme="PM Ujjwala", eligible="maybe", reason="Needs verification: bpl status", benefit="", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        SchemeResult(scheme_id="ladki_bahin", scheme="Ladki Bahin", eligible="maybe", reason="missing caste_category", benefit="", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        SchemeResult(scheme_id="mudra_loan", scheme="Mudra Loan", eligible="maybe", reason="occupation unknown", benefit="", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        SchemeResult(scheme_id="pm_svanidhi", scheme="PM SVANidhi", eligible="maybe", reason="occupation unknown", benefit="", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        SchemeResult(scheme_id="stand_up_india", scheme="Stand Up India", eligible="no", reason="occupation not in allowed list", benefit="", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
    ]

    selected = select_results(results, profile)
    print(f"Total input: {len(results)}, Selected: {len(selected)}")
    for r in selected:
        print(f"  {r.scheme_id:20s} -> {r.eligible:6s} | {r.reason}")
    print()


def test_full_pipeline_sample5_hindi():
    """Test 1: Sample 5 in Hindi through full pipeline (extract -> match -> select_results -> explain_results)."""
    print_section("TEST 1: Sample 5 (Elderly Widow) in Hindi - Full Pipeline")

    samples = load_sample_inputs()
    sample = samples[4]  # Sample 5: Elderly widow
    print(f"Sample: {sample['description']}")
    print(f"Input: {sample['text'][:100]}...")

    # Extract
    profile, missing = extract_profile(sample['text'], debug=False)
    profile_dict = profile.model_dump()
    print(f"Extracted profile: occupation={profile_dict.get('occupation')}, age={profile_dict.get('age')}, gender={profile_dict.get('gender')}, income={profile_dict.get('annual_income')}")

    # Match
    results = match_schemes(profile_dict, sample['text'])
    print(f"Matched {len(results)} schemes")

    # Select
    selected = select_results(results, profile_dict)
    print(f"Selected {len(selected)} schemes for explanation:")
    for r in selected:
        print(f"  {r.scheme_id} ({r.eligible}): {r.reason}")

    # Explain (LLM CALL 1)
    print("\n--- Calling explain_results (LLM CALL 1) ---")
    try:
        explained, summary = explain_results(selected, profile_dict, "hi")
        print(f"Summary (Hindi): {summary}")
        for r in explained:
            print(f"  {r.scheme_id} ({r.eligible}): {r.explanation[:120]}...")
            print(f"    benefit={r.benefit}, link={r.official_link[:60]}...")
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()


def test_chat_sample1_marathi():
    """Test 2: Chat for sample 1 in Marathi: 'Documents kon-kon lagtil?'."""
    print_section("TEST 2: Sample 1 (Farmer) Chat in Marathi")

    samples = load_sample_inputs()
    sample = samples[0]  # Sample 1: Farmer
    print(f"Sample: {sample['description']}")

    profile, _ = extract_profile(sample['text'])
    profile_dict = profile.model_dump()

    results = match_schemes(profile_dict, sample['text'])
    selected = select_results(results, profile_dict)

    # Get scheme IDs for matched schemes
    scheme_ids = [r.scheme_id for r in selected]
    print(f"Matched schemes: {scheme_ids}")

    question = "Documents kon-kon lagtil?"
    print(f"\nQuestion: {question}")
    print("--- Calling answer_chat (LLM CALL 2) ---")

    try:
        answer, sources, translation_failed = answer_chat(question, profile_dict, "mr", [], matched_scheme_ids=scheme_ids)
        print(f"Question: {question}")
        print(f"Answer (Marathi): {answer}")
        print(f"Sources: {sources}")
        print(f"Translation failed: {translation_failed}")
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()


def test_explain_pdf_english():
    """Test 3: explain_pdf in English."""
    print_section("TEST 3: explain_pdf in English")

    # Check for existing PDF in data/pdfs
    pdf_dir = Path(__file__).parent.parent / "data" / "pdfs"
    pdf_files = list(pdf_dir.glob("*.pdf"))

    if pdf_files:
        pdf_path = pdf_files[0]
        print(f"Using existing PDF: {pdf_path}")
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
    else:
        print("No PDF found, creating sample PDF...")
        pdf_bytes = create_sample_pdf()
        if not pdf_bytes:
            print("Failed to create sample PDF")
            return

    # Extract text
    text = extract_text(pdf_bytes)
    print(f"Extracted text length: {len(text)} chars")
    print(f"First 200 chars: {text[:200]}...")

    print("\n--- Calling explain_pdf (LLM CALL 3) ---")
    try:
        summary, key_points, who_is_affected, deadlines = explain_pdf(text, "en")
        print(f"Summary (English): {summary}")
        print(f"Key points: {key_points}")
        print(f"Who is affected: {who_is_affected}")
        print(f"Deadlines: {deadlines}")
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Test 1: select_results (no LLM)
    test_select_results()
    time.sleep(1)

    # Test 2: Sample 5 in Hindi - full pipeline (LLM CALL 1)
    test_full_pipeline_sample5_hindi()
    print("\nSleeping 5 seconds before next LLM call...")
    time.sleep(5)

    # Test 3: Chat for sample 1 in Marathi (LLM CALL 2)
    test_chat_sample1_marathi()
    print("\nSleeping 5 seconds before next LLM call...")
    time.sleep(5)

    # Test 4: explain_pdf in English (LLM CALL 3)
    test_explain_pdf_english()

    print("\n" + "=" * 80)
    print("ALL 3 LLM CALLS COMPLETED")
    print("=" * 80)