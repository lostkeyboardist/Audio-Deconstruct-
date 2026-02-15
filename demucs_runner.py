"""
Demucs stem separation runner.

Uses subprocess to invoke the Demucs CLI, then reorganizes output
into the desired folder structure and naming convention.
"""

import os
import shutil
import subprocess
from pathlib import Path

import torch


def separate_stems(
    input_path,
    output_dir,
    model="htdemucs",
    use_gpu=True,
    shifts=1,
    overlap=0.25,
    selected_stems: list[str] | None = None,
):
    """
    Separate an audio file into stems (drums, bass, other, vocals) using Demucs.

    Args:
        input_path: Path to the input audio file (e.g. .mp3, .wav, .flac).
        output_dir: Base directory where output will be written.
        model: Demucs model name (default: htdemucs).
        use_gpu: If True, use GPU when CUDA is available; otherwise force CPU.
        shifts: Number of random shifts for test-time augmentation. Higher values
            improve quality via averaging multiple predictions, but increase
            processing time (e.g. shifts=4 runs ~4x longer).
        overlap: Overlap ratio between chunks (0.0-1.0). Higher values produce
            smoother stitching at chunk boundaries. Default 0.25.

    Returns:
        dict: {"status": "success"|"failed", "message": str, "output_path": str}
    """
    # Resolve paths to absolute for consistent handling
    input_path = Path(input_path).resolve()
    output_dir = Path(output_dir).resolve()

    # Validate input file
    if not input_path.exists():
        return {
            "status": "failed",
            "message": f"Input file not found: {input_path}",
            "output_path": "",
        }

    if not input_path.is_file():
        return {
            "status": "failed",
            "message": f"Input path is not a file: {input_path}",
            "output_path": "",
        }

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # GPU detection: use CUDA only if requested and available
    # -------------------------------------------------------------------------
    if use_gpu and torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cpu"

    # -------------------------------------------------------------------------
    # Build and run Demucs CLI via subprocess
    # -------------------------------------------------------------------------
    cmd = [
        "demucs",
        "-n", model,
        "-d", device,
        str(input_path),
        "-o", str(output_dir),
    ]

    # Add optional quality/performance params only when non-default
    # Normalize shifts/overlap to avoid string vs int comparison (Combobox may return str)
    try:
        shifts_int = int(shifts) if shifts is not None else 1
    except (TypeError, ValueError):
        shifts_int = 1
    try:
        overlap_float = float(overlap) if overlap is not None else 0.25
    except (TypeError, ValueError):
        overlap_float = 0.25
    if isinstance(shifts_int, int) and shifts_int > 1:
        cmd.extend(["--shifts", str(shifts_int)])
    if isinstance(overlap_float, (int, float)) and overlap_float != 0.25:
        cmd.extend(["--overlap", str(overlap_float)])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600,  # 1 hour max
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "failed",
            "message": "Demucs run timed out after 1 hour",
            "output_path": "",
        }
    except FileNotFoundError:
        return {
            "status": "failed",
            "message": "Demucs CLI not found. Ensure demucs is installed and on PATH.",
            "output_path": "",
        }
    except Exception as e:
        return {
            "status": "failed",
            "message": f"Unexpected error running Demucs: {e}",
            "output_path": "",
        }

    if result.returncode != 0:
        stderr = result.stderr or result.stdout or "No output"
        return {
            "status": "failed",
            "message": f"Demucs failed (exit {result.returncode}): {stderr.strip()}",
            "output_path": "",
        }

    # -------------------------------------------------------------------------
    # Demucs creates: output_dir / model_name / track_name / drums.wav, etc.
    # We need: output_dir / OriginalFileName / OriginalFileName (stem).wav
    # -------------------------------------------------------------------------
    original_name = input_path.stem  # e.g. "song" from "song.mp3"
    model_subdir = output_dir / model
    track_subdir = model_subdir / original_name

    if not track_subdir.exists():
        return {
            "status": "failed",
            "message": f"Demucs did not create expected output at {track_subdir}",
            "output_path": str(output_dir),
        }

    # Target directory: output_dir / OriginalFileName
    target_dir = output_dir / original_name
    target_dir.mkdir(parents=True, exist_ok=True)

    # Dynamically detect stem files: any .wav in the track subdir
    stem_files = list(track_subdir.glob("*.wav"))

    if selected_stems is not None:
        for src in stem_files:
            stem_name = src.stem.lower()
            if stem_name not in selected_stems:
                try:
                    os.remove(src)
                except OSError:
                    pass
        stem_files = [src for src in stem_files if src.exists()]

    # Move and rename: stem.wav -> OriginalFileName (stem).wav
    for src in stem_files:
        stem_name = src.stem  # e.g. "drums" from "drums.wav"
        dest = target_dir / f"{original_name} ({stem_name}).wav"
        shutil.move(str(src), str(dest))

    # -------------------------------------------------------------------------
    # Remove intermediate folders: output_dir/model_name/...
    # This deletes output_dir/htdemucs/ (or whatever model was used)
    # -------------------------------------------------------------------------
    try:
        shutil.rmtree(model_subdir)
    except OSError:
        # Non-fatal: stems were moved; intermediate folder removal failed
        pass

    return {
        "status": "success",
        "message": f"Stems saved to {target_dir}",
        "output_path": str(target_dir),
    }
