"""
Engine layer test script.

Tests convert_audio and separate_stems with a single audio file.
Edit TEST_FILE below with a full path to a real audio file before running.
"""

from pathlib import Path

from converter_runner import convert_audio
from demucs_runner import separate_stems

# -----------------------------------------------------------------------------
# EDIT THIS: Full path to an audio file (mp3, wav, flac, etc.)
# -----------------------------------------------------------------------------
TEST_FILE = r"C:\Users\Lenovo\Music\music\Music\3 Pareshaan.mp3"

# Demucs model: htdemucs_ft = fine-tuned, higher quality (larger download)
TEST_MODEL = "htdemucs_ft"

# Output folder for this test run (created inside project directory)
PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "engine_output_test"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("ENGINE TEST")
    print(f"Input file: {TEST_FILE}")
    print(f"Output dir: {OUTPUT_DIR}")
    print("=" * 60)

    # -------------------------------------------------------------------------
    # Test 1: convert_audio - convert TEST_FILE to wav
    # -------------------------------------------------------------------------
    print("\n--- Test 1: convert_audio (to wav) ---")
    try:
        result = convert_audio(
            input_path=TEST_FILE,
            output_dir=OUTPUT_DIR,
            output_format="wav",
        )
        print("Result:", result)
        print(f"  status: {result['status']}")
        print(f"  message: {result['message']}")
        print(f"  output_path: {result['output_path']}")
    except Exception as e:
        print(f"Error: {e}")

    # -------------------------------------------------------------------------
    # Test 2: separate_stems - separate TEST_FILE into stems
    # Higher-quality mode: shifts=4 and overlap=0.5 (slower but better results)
    # -------------------------------------------------------------------------
    print("\n--- Test 2: separate_stems ---")
    try:
        result = separate_stems(
            input_path=TEST_FILE,
            output_dir=OUTPUT_DIR,
            model=TEST_MODEL,
            use_gpu=True,
            shifts=4,
            overlap=0.5,
        )
        print("Result:", result)
        print(f"  status: {result['status']}")
        print(f"  message: {result['message']}")
        print(f"  output_path: {result['output_path']}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "=" * 60)
    print("Done.")
    print("=" * 60)


if __name__ == "__main__":
    main()
