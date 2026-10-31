"""Test script for scheme matching functionality."""
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.extract import extract_profile
from backend.match import match_schemes, load_schemes
from backend.schemas import Profile
from backend.rules import check_rules


def load_sample_inputs() -> List[Dict[str, Any]]:
    """Load sample user inputs from JSON file."""
    with open(Path(__file__).parent / "sample_inputs.json", "r", encoding="utf-8") as f:
        return json.load(f)


def load_expected_results() -> Dict[str, List[str]]:
    """Load expected results from sample_inputs.json."""
    samples = load_sample_inputs()
    expected = {}
    for sample in samples:
        key = sample["description"]
        expected[key] = {
            "eligible": sample.get("expected_eligible_schemes", []),
            "maybe": sample.get("expected_maybe_schemes", []),
            "not_eligible": sample.get("expected_not_eligible_schemes", []),
        }
    return expected


def is_occupation_maybe(reason: str) -> bool:
    """Check if a reason indicates unknown occupation."""
    reason_lower = reason.lower()
    return "occupation" in reason_lower and ("unknown" in reason_lower or "missing" in reason_lower or "not in allowed" in reason_lower)


def sort_schemes_for_display(results: List) -> List:
    """
    Sort schemes for display:
    - First: "yes" verdicts
    - Then: "maybe" verdicts (non-occupation reasons first)
    - Then: "maybe" with occupation reasons (max 2)
    - Last: "no" verdicts
    """
    yes_results = [r for r in results if r.eligible == "yes"]

    maybe_results = [r for r in results if r.eligible == "maybe"]
    maybe_occupation = [r for r in maybe_results if is_occupation_maybe(r.reason) or is_occupation_maybe(r.source_quote or "")]
    maybe_other = [r for r in maybe_results if r not in maybe_occupation]

    no_results = [r for r in results if r.eligible == "no"]

    # Limit occupation maybes to 2
    maybe_occupation = maybe_occupation[:2]

    return yes_results + maybe_other + maybe_occupation + no_results


def get_verdict_status(expected_verdict: str, actual_verdict: str) -> Tuple[str, bool, bool]:
    """
    Determine match status.
    Returns: (status_symbol, is_fail, is_warn)
    - FAIL: expected "maybe" but got "yes", or expected "no" but got "yes"/"maybe"
    - WARN: expected "yes" but got "maybe" (counts as pass for exit code)
    - PASS: all other matches
    """
    if expected_verdict == "yes":
        if actual_verdict == "yes":
            return "✓", False, False
        elif actual_verdict == "maybe":
            return "⚠", False, True  # WARN but not fail
        else:  # no
            return "✗", True, False
    elif expected_verdict == "maybe":
        if actual_verdict == "maybe":
            return "✓", False, False
        elif actual_verdict == "yes":
            return "✗", True, False  # FAIL - should not be definitive yes
        else:  # no
            return "✗", True, False
    else:  # expected "no"
        if actual_verdict == "no":
            return "✓", False, False
        else:  # yes or maybe
            return "✗", True, False


def print_match_results():
    """Run match_schemes for each sample and print results vs expected."""
    samples = load_sample_inputs()
    expected_results = load_expected_results()

    # Also load all schemes to check rules for all (not just top 5)
    schemes = load_schemes()
    scheme_map = {s["id"]: s for s in schemes}

    print("=" * 140)
    print("SCHEME MATCHING TEST RESULTS")
    print("=" * 140)

    total_tests = 0
    passes = 0
    warns = 0
    fails = 0
    all_mismatches = []

    for i, sample in enumerate(samples, 1):
        print(f"\n--- Sample {i}: {sample['description']} ---")
        print(f"Input text: {sample['text']}")
        print(f"Language: {sample['language']}")

        # Extract profile
        profile, missing_fields = extract_profile(sample['text'])
        profile_dict = profile.model_dump()

        print(f"\nExtracted Profile:")
        for k, v in profile_dict.items():
            print(f"  {k:20s}: {v}")
        print(f"Missing fields: {missing_fields}")

        # Match schemes (get top 5 for display)
        results = match_schemes(profile_dict, sample['text'])

        # Also run check_rules on ALL schemes to get reasons for all
        all_scheme_results = []
        for scheme in schemes:
            verdict, reasons, missing = check_rules(profile_dict, scheme)
            all_scheme_results.append({
                "scheme_id": scheme["id"],
                "scheme_name": scheme["name"],
                "eligible": verdict,
                "reasons": reasons,
                "missing_fields": missing,
            })

        # Sort for display
        # Create mock result objects for sorting
        class MockResult:
            def __init__(self, d):
                self.scheme_id = d["scheme_id"]
                self.scheme_name = d["scheme_name"]
                self.eligible = d["eligible"]
                self.reason = d["reasons"][0] if d["reasons"] else ""
                self.source_quote = ""

        mock_results = [MockResult(r) for r in all_scheme_results]
        sorted_results = sort_schemes_for_display(mock_results)

        # Build actual verdicts map
        actual = {}
        for r in all_scheme_results:
            actual[r["scheme_id"]] = r["eligible"]

        expected = expected_results[sample['description']]

        # Evaluate all schemes
        print(f"\n{'Scheme':30s} | {'Actual':8s} | {'Expected':15s} | Status")
        print("-" * 75)

        for scheme_id in expected["eligible"]:
            actual_verdict = actual.get(scheme_id, "no")
            status, is_fail, is_warn = get_verdict_status("yes", actual_verdict)
            if is_fail:
                fails += 1
                all_mismatches.append(f"Sample {i}: {scheme_id} expected 'yes' but got '{actual_verdict}'")
            elif is_warn:
                warns += 1
            else:
                passes += 1
            total_tests += 1
            print(f"{scheme_id:30s} | {actual_verdict:8s} | {'yes':15s} | {status}")

        for scheme_id in expected["maybe"]:
            actual_verdict = actual.get(scheme_id, "no")
            status, is_fail, is_warn = get_verdict_status("maybe", actual_verdict)
            if is_fail:
                fails += 1
                all_mismatches.append(f"Sample {i}: {scheme_id} expected 'maybe' but got '{actual_verdict}'")
            elif is_warn:
                warns += 1
            else:
                passes += 1
            total_tests += 1
            print(f"{scheme_id:30s} | {actual_verdict:8s} | {'maybe':15s} | {status}")

        for scheme_id in expected["not_eligible"]:
            actual_verdict = actual.get(scheme_id, "no")
            status, is_fail, is_warn = get_verdict_status("no", actual_verdict)
            if is_fail:
                fails += 1
                all_mismatches.append(f"Sample {i}: {scheme_id} expected 'no' but got '{actual_verdict}'")
            elif is_warn:
                warns += 1
            else:
                passes += 1
            total_tests += 1
            print(f"{scheme_id:30s} | {actual_verdict:8s} | {'no':15s} | {status}")

        # Print details for ALL schemes (sorted)
        print(f"\nDetails (all schemes, sorted):")
        for r in sorted_results:
            reason_str = r.reason
            if r.source_quote:
                reason_str += f" | Quote: {r.source_quote[:80]}..."
            # Find full reason from all_scheme_results
            full = next((x for x in all_scheme_results if x["scheme_id"] == r.scheme_id), None)
            if full and full["reasons"]:
                reason_str = "; ".join(full["reasons"])
            print(f"  {r.scheme_id:30s} -> {r.eligible:6s} | {reason_str}")

    print("\n" + "=" * 140)
    print(f"SUMMARY: {passes} PASS, {warns} WARN, {fails} FAIL out of {total_tests} tests")
    if fails > 0:
        print(f"\nFAILURES ({fails}):")
        for m in all_mismatches:
            print(f"  - {m}")
    if warns > 0:
        print(f"\nWARNINGS ({warns}): expected 'yes' but got 'maybe' (treating as pass)")
    print("=" * 140)

    return passes, warns, fails, total_tests


if __name__ == "__main__":
    passes, warns, fails, total = print_match_results()
    sys.exit(1 if fails > 0 else 0)