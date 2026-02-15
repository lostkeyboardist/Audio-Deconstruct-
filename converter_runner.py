"""
Audio format converter runner.

Uses subprocess to invoke FFmpeg for converting audio files
between wav, mp3, and mpeg formats.
"""

import shutil
import subprocess
from pathlib import Path


def _ffmpeg_available():
    """Return True if ffmpeg is on PATH, False otherwise."""
    return shutil.which("ffmpeg") is not None


def convert_audio(
    input_path,
    output_dir,
    output_format="wav",
    bitrate="320k",
    sample_rate=None,
):
    """
    Convert an audio file to another format using FFmpeg.

    Args:
        input_path: Path to the input audio file.
        output_dir: Directory where the converted file will be saved.
        output_format: Target format: "mp3", "wav", or "mpeg".
        bitrate: Bitrate for lossy formats (mp3, mpeg). Ignored for wav.
        sample_rate: Target sample rate in Hz. If None, preserve original.

    Returns:
        dict: {"status": "success"|"failed", "message": str, "output_path": str}
    """
    input_path = Path(input_path).resolve()
    output_dir = Path(output_dir).resolve()

    # -------------------------------------------------------------------------
    # Validate output_format
    # -------------------------------------------------------------------------
    output_format = output_format.lower()
    allowed_formats = ("mp3", "wav", "mpeg", "flac")
    if output_format not in allowed_formats:
        return {
            "status": "failed",
            "message": f"Unsupported output_format: {output_format}. Use: {allowed_formats}",
            "output_path": "",
        }

    # -------------------------------------------------------------------------
    # Detect FFmpeg availability
    # -------------------------------------------------------------------------
    if not _ffmpeg_available():
        return {
            "status": "failed",
            "message": "FFmpeg not found. Install FFmpeg and add it to PATH.",
            "output_path": "",
        }

    # -------------------------------------------------------------------------
    # Validate input file
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # Build output path: output_dir / original_stem.new_extension
    # Preserve original filename, change extension only.
    # -------------------------------------------------------------------------
    format_extensions = {"mp3": ".mp3", "wav": ".wav", "mpeg": ".mpeg", "flac": ".flac"}
    ext = format_extensions[output_format]
    output_filename = input_path.stem + ext
    output_path = output_dir / output_filename

    output_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # Build FFmpeg command
    # -------------------------------------------------------------------------
    cmd = ["ffmpeg", "-y", "-i", str(input_path)]

    # -y: overwrite output without prompting

    if sample_rate is not None:
        cmd.extend(["-ar", str(sample_rate)])

    if output_format == "mp3":
        cmd.extend(["-f", "mp3", "-b:a", bitrate])
    elif output_format == "mpeg":
        cmd.extend(["-f", "mp2", "-b:a", bitrate])
    elif output_format == "flac":
        cmd.extend(["-f", "flac"])
    # wav: no bitrate flag, format inferred from extension

    cmd.append(str(output_path))

    # -------------------------------------------------------------------------
    # Run FFmpeg
    # -------------------------------------------------------------------------
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "failed",
            "message": "FFmpeg timed out after 1 hour",
            "output_path": "",
        }
    except Exception as e:
        return {
            "status": "failed",
            "message": f"Unexpected error running FFmpeg: {e}",
            "output_path": "",
        }

    if result.returncode != 0:
        stderr = result.stderr or result.stdout or "No output"
        return {
            "status": "failed",
            "message": f"FFmpeg failed (exit {result.returncode}): {stderr.strip()}",
            "output_path": "",
        }

    if not output_path.exists():
        return {
            "status": "failed",
            "message": "FFmpeg completed but output file was not created",
            "output_path": "",
        }

    return {
        "status": "success",
        "message": f"Converted to {output_path}",
        "output_path": str(output_path),
    }
