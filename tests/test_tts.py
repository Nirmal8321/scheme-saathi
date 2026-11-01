#!/usr/bin/env python3
"""Test script for TTS module. Generates Marathi, Hindi, and English samples into ./tts_cache and prints file sizes."""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.tts import synthesize, CACHE_DIR


def main():
    # Test samples for each language
    samples = [
        ("mr", "नमस्कार, हा मराठी भाषेत एक परीक्षण आहे."),
        ("hi", "नमस्ते, यह हिंदी में एक परीक्षण है।"),
        ("en", "Hello, this is a test in English."),
    ]

    print("Generating TTS samples...")
    print(f"Cache directory: {CACHE_DIR}")
    print("-" * 50)

    for lang, text in samples:
        print(f"\nLanguage: {lang}")
        print(f"Text: {text}")

        try:
            audio_bytes = synthesize(text, lang)
            size = len(audio_bytes)

            # Find the cache file
            import hashlib
            cache_key = f"{text}|{lang}"
            cache_hash = hashlib.sha256(cache_key.encode('utf-8')).hexdigest()[:16]
            cache_file = CACHE_DIR / f"{cache_hash}.mp3"

            print(f"Cache file: {cache_file.name}")
            print(f"Size: {size:,} bytes ({size / 1024:.1f} KB)")

        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)

    print("\n" + "=" * 50)
    print("All samples generated successfully!")

    # List all cache files
    print("\nCache contents:")
    for f in sorted(CACHE_DIR.glob("*.mp3")):
        size = f.stat().st_size
        print(f"  {f.name}: {size:,} bytes ({size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()