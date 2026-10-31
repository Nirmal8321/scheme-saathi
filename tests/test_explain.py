"""Test script for LLM #3 explainer functionality."""
import json
import sys
import os
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
        page.insert_text((50, 120), "Benefit: Rs 6,000 per year in 3 installments\n")
        page.insert_text((50, 140), "Eligibility: Landholding farmer families with cultivable land\n")
        page.insert_text((50, 160), "Apply at: pmkisan.gov.in or nearest CSC center\n")
        page.insert_text((50, 180), "Deadline: Ongoing scheme, no deadline\n")
        page.insert_text((50, 200), "Contact: 155261 or pmkisan.gov.in\n")
        pdf_bytes = doc.tobytes()
        doc.close()
        return pdf_bytes
    except Exception:
        return b""


def test_select_results():
    """Test the select_results function."""
    print("=" * 80)
    print("TESTING select_results")
    print("=" * 80)

    from backend.schemas import SchemeResult

    # Create mock results with different verdicts
    results = [
        SchemeResult(scheme_id="pm_kisan", scheme="PM-KISAN", eligible="yes", reason="Eligible farmer", benefit="Rs 6000/year", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        SchemeResult(scheme_id="namo_shetkari", scheme="Namo Shetkari", eligible="yes", reason="Maharashtra farmer", benefit="Rs 6000/year", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        SchemeResult(scheme_id="pm_awas", scheme="PM Awas", eligible="maybe", reason="Needs verification: house ownership", benefit="", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        SchemeResult(scheme_id="pm_ujjwala", scheme="PM Ujjwala", eligible="maybe", reason="Needs verification: bpl status", benefit="", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        SchemeResult(scheme_id="ladki_bahin", scheme="Ladki Bahin", eligible="maybe", reason="missing caste_category", benefit="", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        SchemeResult(scheme_id="mudra_loan", scheme="Mudra Loan", eligible="maybe", reason="occupation unknown", benefit="", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        SchemeResult(scheme_id="pm_svanidhi", scheme="PM SVANidhi", eligible="maybe", reason="occupation unknown", benefit="", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
        SchemeResult(scheme_id="stand_up_india", scheme="Stand Up India", eligible="no", reason="occupation not in allowed list", benefit="", documents=[], how_to_apply="", official_link="", source_quote="", explanation=""),
    ]

    selected = select_results(results)
    print(f"Total input: {len(results)}, Selected: {len(selected)}")
    for r in selected:
        print(f"  {r.scheme_id:20s} -> {r.eligible:6s} | {r.reason}")
    print()


def test_explain_results():
    """Test explain_results for sample users 1 and 2 in mr, hi, en."""
    print("=" * 80)
    print("TESTING explain_results")
    print("=" * 80)

    samples = load_sample_inputs()

    for lang in ["mr", "hi", "en"]:
        print(f"\n--- Language: {lang} ---")
        for i, sample in enumerate(samples[:2]):  # Sample 1 and 2
            print(f"\nSample {i+1}: {sample['description']}")

            # Extract profile
            profile, _ = extract_profile(sample['text'])
            profile_dict = profile.model_dump()

            # Match schemes
            results = match_schemes(profile_dict, sample['text'])

            # Select top results
            selected = select_results(results)

            # Explain
            try:
                explained, summary = explain_results(selected, profile_dict, lang)
                print(f"  Summary ({lang}): {summary}")
                for r in explained[:2]:
                    print(f"    {r.scheme_id} ({r.eligible}): {r.explanation}")
            except Exception as e:
                print(f"  ERROR: {e}")


def test_answer_chat():
    """Test chat with 'Documents kon-kon lagtil?' for sample 1."""
    print("\n" + "=" * 80)
    print("TESTING answer_chat")
    print("=" * 80)

    samples = load_sample_inputs()

    for lang in ["mr", "hi", "en"]:
        print(f"\n--- Language: {lang} ---")
        sample = samples[0]  # Farmer sample

        profile, _ = extract_profile(sample['text'])
        profile_dict = profile.model_dump()

        results = match_schemes(profile_dict, sample['text'])
        selected = select_results(results)

        question = "Documents kon-kon lagtil?" if lang == "mr" else \
                   "कौन से दस्तावेज लगेंगे?" if lang == "hi" else \
                   "What documents are needed?"

        try:
            answer, sources = answer_chat(question, profile_dict, lang, [])
            print(f"  Question: {question}")
            print(f"  Answer ({lang}): {answer}")
            print(f"  Sources: {sources}")
        except Exception as e:
            print(f"  ERROR: {e}")


def test_explain_pdf():
    """Test explain_pdf on a sample PDF."""
    print("\n" + "=" * 80)
    print("TESTING explain_pdf")
    print("=" * 80)

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

    for lang in ["mr", "hi", "en"]:
        print(f"\n--- Language: {lang} ---")
        try:
            summary, key_points, who_is_affected, deadlines = explain_pdf(text, lang)
            print(f"  Summary ({lang}): {summary}")
            print(f"  Key points: {key_points}")
            print(f"  Who is affected: {who_is_affected}")
            print(f"  Deadlines: {deadlines}")
        except Exception as e:
            print(f"  ERROR: {e}")


def test_full_pipeline():
    """Test the full pipeline for all 5 samples in all languages."""
    print("\n" + "=" * 80)
    print("FULL PIPELINE TEST (all samples, all languages)")
    print("=" * 80)

    samples = load_sample_inputs()

    for sample in samples:
        print(f"\n--- {sample['description']} ---")

        for lang in ["mr", "hi", "en"]:
            print(f"\n  Language: {lang}")

            # Extract
            profile, missing = extract_profile(sample['text'], debug=False)
            profile_dict = profile.model_dump()

            # Match
            results = match_schemes(profile_dict, sample['text'])

            # Select
            selected = select_results(results)

            # Explain
            try:
                explained, summary = explain_results(selected, profile_dict, lang)
                print(f"    Summary: {summary[:80]}...")
                for r in explained[:2]:
                    print(f"    {r.scheme_id} ({r.eligible}): {r.explanation[:80]}...")
            except Exception as e:
                print(f"    ERROR in explain: {e}")


if __name__ == "__main__":
    test_select_results()
    test_explain_results()
    test_answer_chat()
    test_explain_pdf()
    test_full_pipeline()

    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETED")
    print("=" * 80)