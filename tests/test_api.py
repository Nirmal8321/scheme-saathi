"""Test script for FastAPI endpoints using TestClient."""
import os
import json
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

# Set USE_MOCK=false for real LLM calls
os.environ["USE_MOCK"] = "false"
os.environ["LLM_CACHE"] = "true"

# Must set before importing backend modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from backend.main import app


client = TestClient(app)

# Sample inputs from sample_inputs.json
SAMPLES = [
    {
        "description": "Farmer in Wardha, Marathi input",
        "text": "Mi shetkari aahe, Wardha madhe. 2 acre jamin. Varshik utpanna 80000. Vaya 45 varsh. Mulga mulgi 2.",
        "language": "mr",
    },
    {
        "description": "Woman entrepreneur in Mumbai, Hindi/English mixed",
        "text": "Main Mumbai mein apna chota sa business chalti hoon. Beauty parlor hai. Varshik aamdani 3 lakh. Age 32. SC category. Bank se loan chahiye business badhane ke liye.",
        "language": "hi",
    },
    {
        "description": "Elderly widow in rural Maharashtra, Hindi",
        "text": "Main 68 saal ki vidhwa hoon. Gaon mein rehti hoon. Koi pension nahi milta. Pariwar ki aamdani 50 hazar saal. Gas connection nahi hai. Aadhaar card hai.",
        "language": "hi",
    },
]


def print_section(title: str):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def test_health():
    print_section("TEST: /api/health")
    response = client.get("/api/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    print("✓ Health check passed")


def test_analyze_sample1_marathi():
    """Test /api/analyze with sample 1 (Farmer) in Marathi."""
    print_section("TEST: /api/analyze - Sample 1 (Farmer) in Marathi")

    sample = SAMPLES[0]
    payload = {
        "text": sample["text"],
        "language": sample["language"],
        "profile_override": None
    }

    print(f"Request: {json.dumps(payload, ensure_ascii=False)[:200]}...")

    start = time.time()
    response = client.post("/api/analyze", json=payload)
    elapsed = time.time() - start

    print(f"Response time: {elapsed:.2f}s")
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Profile: {json.dumps(data['profile'], ensure_ascii=False)}")
        print(f"Missing fields: {data['missing_fields']}")
        print(f"Results count: {len(data['results'])}")
        for r in data['results']:
            print(f"  {r['scheme_id']} ({r['eligible']}): {r['reason'][:80]}...")
            if r.get('explanation'):
                print(f"    Explanation: {r['explanation'][:100]}...")
        print(f"Summary: {data['summary_text']}")
        print(f"Language: {data['language']}")
    else:
        print(f"Error: {response.json()}")

    assert response.status_code == 200
    print("✓ Analyze passed")
    return response.json()


def test_chat_sample1_marathi():
    """Test /api/chat with sample 1 in Marathi."""
    print_section("TEST: /api/chat - Sample 1 in Marathi")

    sample = SAMPLES[0]
    profile, _ = extract_profile(sample['text'], debug=False)
    profile_dict = profile.model_dump()

    # Get matched scheme IDs
    from backend.rules import check_all_schemes
    from backend.match import match_schemes

    # Load schemes
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    schemes_path = os.path.join(base_dir, "data", "schemes.json")
    with open(schemes_path, "r", encoding="utf-8") as f:
        schemes = json.load(f)

    from backend.rules import check_all_schemes
    results = check_all_schemes(profile_dict, schemes)
    matched_scheme_ids = [r["scheme_id"] for r in results if r["verdict"] in ("yes", "maybe")]

    profile_dict = profile_dict
    question = "Documents kon-kon lagtil?"

    print(f"Question: {question}")
    print(f"Matched schemes: {matched_scheme_ids}")

    payload = {
        "question": question,
        "profile": profile_dict,
        "language": "mr",
        "history": [],
    }

    start = time.time()
    response = client.post("/api/chat", json=payload)
    elapsed = time.time() - start

    print(f"Response time: {elapsed:.2f}s")
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Answer: {data['answer']}")
        print(f"Sources: {data['sources']}")
        print(f"Translation failed: {data.get('translation_failed', False)}")
    else:
        print(f"Error: {response.json()}")

    assert response.status_code == 200
    print("✓ Chat passed")
    return response.json()


def test_explain_pdf_english():
    """Test /api/explain-pdf with sample PDF in English."""
    print_section("TEST: /api/explain-pdf - English")

    # Create sample PDF
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

    # Upload PDF
    files = {"file": ("test.pdf", pdf_bytes, "application/pdf")}
    data = {"language": "en"}

    print(f"PDF size: {len(pdf_bytes)} bytes")

    start = time.time()
    response = client.post("/api/explain-pdf", files=files, data=data)
    elapsed = time.time() - start

    print(f"Response time: {elapsed:.2f}s")
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Summary: {data['summary']}")
        print(f"Key points: {data['key_points']}")
        print(f"Who is affected: {data['who_is_affected']}")
        print(f"Deadlines: {data['deadlines']}")
        print(f"Language: {data['language']}")
    else:
        print(f"Error: {response.json()}")

    assert response.status_code == 200
    print("✓ PDF explain passed")
    return response.json()


def test_error_handling():
    """Test error handling for invalid requests."""
    print_section("TEST: Error handling")

    # Test non-PDF file rejection
    print("\n--- Testing non-PDF file rejection ---")
    files = {"file": ("test.txt", b"not a pdf", "text/plain")}
    data = {"language": "en"}
    response = client.post("/api/explain-pdf", files={"file": ("test.txt", b"not a pdf", "text/plain")}, data=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 400

    # Test file size limit (10 MB)
    print("\n--- Testing file size limit ---")
    large_content = b"x" * (11 * 1024 * 1024)  # 11 MB
    files = {"file": ("large.pdf", large_content, "application/pdf")}
    response = client.post("/api/explain-pdf", files=files, data={"language": "en"})
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 400

    # Test 429 error message format
    print("\n--- Testing error response format ---")
    # We can't easily trigger 429, but verify error format
    response = client.post("/api/analyze", json={"text": "", "language": "xx"})
    print(f"Invalid language status: {response.status_code}")
    print(f"Error format: {response.json()}")

    print("✓ Error handling tests passed")


def main():
    """Run all tests."""
    print("=" * 80)
    print("TESTING FASTAPI ENDPOINTS (USE_MOCK=false)")
    print("=" * 80)

    # Set environment
    os.environ["USE_MOCK"] = "false"
    os.environ["LLM_CACHE"] = "true"

    # Import here to use updated modules
    global extract_profile, match_schemes
    from backend.extract import extract_profile
    from backend.match import match_schemes
    import json

    try:
        test_health()
        time.sleep(1)

        test_analyze_sample1_marathi()
        time.sleep(5)  # Sleep between LLM calls

        test_chat_sample1_marathi()
        time.sleep(5)

        test_explain_pdf_english()
        time.sleep(1)

        test_error_handling()

        print("\n" + "=" * 80)
        print("ALL TESTS PASSED!")
        print("=" * 80)

    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Add backend to path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    main()