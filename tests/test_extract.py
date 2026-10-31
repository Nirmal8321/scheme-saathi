"""Test script for profile extraction functionality."""
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.extract import extract_profile
from backend.schemas import Profile


def load_sample_inputs() -> List[Dict[str, Any]]:
    """Load sample user inputs from JSON file."""
    with open(Path(__file__).parent / "sample_inputs.json", "r", encoding="utf-8") as f:
        return json.load(f)


def print_profile_table(samples: List[Dict[str, Any]]):
    """Print extracted profiles in a table format."""
    print("=" * 120)
    print("PROFILE EXTRACTION TEST RESULTS")
    print("=" * 120)

    for i, sample in enumerate(samples, 1):
        print(f"\n--- Sample {i}: {sample['description']} ---")
        print(f"Input text: {sample['text']}")
        print(f"Language: {sample['language']}")

        try:
            # Use debug=True to see raw LLM JSON
            profile, missing_fields = extract_profile(sample['text'], debug=True)

            # Convert profile to dict for printing
            profile_dict = profile.model_dump()

            print(f"\nExtracted Profile:")
            print(f"  occupation        : {profile_dict['occupation']}")
            print(f"  age               : {profile_dict['age']}")
            print(f"  gender            : {profile_dict['gender']}")
            print(f"  state             : {profile_dict['state']}")
            print(f"  district          : {profile_dict['district']}")
            print(f"  annual_income     : {profile_dict['annual_income']}")
            print(f"  income_note       : {profile_dict['income_note']}")
            print(f"  land_acres        : {profile_dict['land_acres']}")
            print(f"  caste_category    : {profile_dict['caste_category']}")
            print(f"  family_members    : {profile_dict['family_members']}")

            print(f"\nMissing fields: {missing_fields}")

            # Check against expected
            expected_eligible = sample.get('expected_eligible_schemes', [])
            expected_maybe = sample.get('expected_maybe_schemes', [])
            expected_not = sample.get('expected_not_eligible_schemes', [])
            print(f"\nExpected eligible: {expected_eligible}")
            print(f"Expected maybe: {expected_maybe}")
            print(f"Expected not eligible: {expected_not}")

        except Exception as e:
            print(f"  ERROR: {e}")

    print("\n" + "=" * 120)
    print("TEST COMPLETED")
    print("=" * 120)


if __name__ == "__main__":
    samples = load_sample_inputs()
    print_profile_table(samples)