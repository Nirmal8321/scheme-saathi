#!/usr/bin/env python3
"""Test script for STT module. Takes a WAV file path as argument, prints transcript and time taken."""
import sys
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.stt import transcribe


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_stt.py <path_to_wav_file> [language]")
        print("Default language: en")
        sys.exit(1)

    wav_path = Path(sys.argv[1])
    language = sys.argv[2] if len(sys.argv) > 2 else "en"

    if not wav_path.exists():
        print(f"Error: File not found: {wav_path}")
        sys.exit(1)

    if not wav_path.is_file():
        print(f"Error: Not a file: {wav_path}")
        sys.exit(1)

    # Read audio bytes
    audio_bytes = wav_path.read_bytes()

    print(f"Transcribing: {wav_path}")
    print(f"Language: {language}")
    print(f"Audio size: {len(audio_bytes)} bytes")
    print("-" * 40)

    # Time the transcription
    start_time = time.perf_counter()
    try:
        text = transcribe(audio_bytes, language)
        elapsed = time.perf_counter() - start_time

        print(f"Transcript: {text}")
        print(f"Time taken: {elapsed:.3f} seconds")

    except Exception as e:
        elapsed = time.perf_counter() - start_time
        print(f"Error: {e}")
        print(f"Time taken: {elapsed:.3f} seconds")
        sys.exit(1)


if __name__ == "__main__":
    main()