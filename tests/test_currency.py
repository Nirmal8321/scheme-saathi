#!/usr/bin/env python3
"""Unit tests for money post-processing in Hindi and Marathi."""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.explain import _post_process_currency


def test_hindi_currency():
    """Test Hindi currency formatting."""
    test_cases = [
        # (input, expected_output)
        ("5 lakh rupees", "5 लाख रुपये"),
        ("Rs 2.67 lakh", "2.67 लाख रुपये"),
        ("Rs 6,000", "6,000 रुपये"),
        ("Rs 5 lakh", "5 लाख रुपये"),
        ("Rs 1 crore", "1 करोड़ रुपये"),
        ("10 lakh rupees", "10 लाख रुपये"),
        ("Rs 2.67 crore", "2.67 करोड़ रुपये"),
        ("5 lakh", "5 लाख"),
        ("1 crore", "1 करोड़"),
        ("Rs 100", "100 रुपये"),
        ("Rs 5,00,000", "5,00,000 रुपये"),
    ]

    for input_text, expected in test_cases:
        result = _post_process_currency(input_text, "hi")
        assert result == expected, f"Failed for '{input_text}': got '{result}', expected '{expected}'"
        print(f"✓ '{input_text}' -> '{result}'")

    print("All Hindi tests passed!")


def test_marathi_currency():
    """Test Marathi currency formatting."""
    test_cases = [
        ("5 lakh rupees", "5 लाख रुपये"),
        ("Rs 2.67 lakh", "2.67 लाख रुपये"),
        ("Rs 6,000", "6,000 रुपये"),
        ("Rs 5 lakh", "5 लाख रुपये"),
        ("Rs 1 crore", "1 करोड रुपये"),
        ("10 lakh rupees", "10 लाख रुपये"),
        ("Rs 2.67 crore", "2.67 करोड रुपये"),
        ("5 lakh", "5 लाख"),
        ("1 crore", "1 करोड"),
        ("Rs 100", "100 रुपये"),
        ("Rs 5,00,000", "5,00,000 रुपये"),
    ]

    for input_text, expected in test_cases:
        result = _post_process_currency(input_text, "mr")
        assert result == expected, f"Failed for '{input_text}': got '{result}', expected '{expected}'"
        print(f"✓ '{input_text}' -> '{result}'")

    print("All Marathi tests passed!")


def test_english_unchanged():
    """Test that English text is unchanged."""
    test_cases = [
        "5 lakh rupees",
        "Rs 2.67 lakh",
        "Rs 6,000",
    ]

    for input_text in test_cases:
        result = _post_process_currency(input_text, "en")
        assert result == input_text, f"English text changed: got '{result}', expected '{input_text}'"
        print(f"✓ '{input_text}' unchanged")


def test_mixed_text():
    """Test currency in mixed text."""
    test_cases = [
        ("The benefit is Rs 5 lakh per year", "The benefit is 5 लाख रुपये per year"),
        ("You get 2.67 lakh rupees as subsidy", "You get 2.67 लाख रुपये as subsidy"),
        ("Amount: Rs 6,000", "Amount: 6,000 रुपये"),
    ]

    for input_text, expected in test_cases:
        result = _post_process_currency(input_text, "hi")
        assert result == expected, f"Failed for '{input_text}': got '{result}', expected '{expected}'"
        print(f"✓ Mixed text: '{input_text}' -> '{result}'")


if __name__ == "__main__":
    print("Testing Hindi currency...")
    test_hindi_currency()
    print()
    print("Testing Marathi currency...")
    test_marathi_currency()
    print()
    print("Testing English unchanged...")
    test_english_unchanged()
    print()
    print("Testing mixed text...")
    test_mixed_text()
    print()
    print("All tests passed!")