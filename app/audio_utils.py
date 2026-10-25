import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

def run_command(cmd: list) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False
    )

def get_audio_metadata(file_path: Path) -> Dict[str, Any]:
    """Extract audio duration, channels, sample rate, and format using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(file_path)
    ]
    try:
        proc = run_command(cmd)
        if proc.returncode == 0:
            data = json.loads(proc.stdout)
            format_info = data.get("format", {})
            duration = float(format_info.get("duration", 0.0))
            bitrate = int(format_info.get("bit_rate", 0)) if format_info.get("bit_rate") else None
            size_bytes = int(format_info.get("size", file_path.stat().st_size))

            audio_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), {})
            sample_rate = audio_stream.get("sample_rate", "Unknown")
            channels = audio_stream.get("channels", 1)

            return {
                "duration": duration,
                "duration_formatted": format_seconds(duration),
                "size_mb": round(size_bytes / (1024 * 1024), 2),
                "bitrate_kbps": round(bitrate / 1000) if bitrate else None,
                "sample_rate": sample_rate,
                "channels": channels,
                "format_name": format_info.get("format_name", file_path.suffix.lstrip("."))
            }
    except Exception as e:
        print(f"Error probing audio: {e}")

    # Fallback to file size and estimated duration
    size_mb = round(file_path.stat().st_size / (1024 * 1024), 2)
    return {
        "duration": 0,
        "duration_formatted": "00:00:00",
        "size_mb": size_mb,
        "bitrate_kbps": None,
        "sample_rate": "44100",
        "channels": 2,
        "format_name": file_path.suffix.lstrip(".")
    }

def optimize_audio_for_gemini(input_path: Path, output_path: Path) -> Path:
    """
    If file is very large (e.g., uncompressed WAV > 100MB), compress to high quality MP3 (128kbps)
    to speed up network upload without losing voice fidelity.
    """
    if input_path.suffix.lower() == ".mp3" and input_path.stat().st_size < 100 * 1024 * 1024:
        return input_path

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vn",
        "-ar", "16000",
        "-ac", "1",
        "-b:a", "64k",
        str(output_path)
    ]
    proc = run_command(cmd)
    if proc.returncode == 0 and output_path.exists():
        return output_path
    return input_path

def format_seconds(seconds: float) -> str:
    """Convert seconds to HH:MM:SS format."""
    total_sec = int(round(seconds))
    hours = total_sec // 3600
    minutes = (total_sec % 3600) // 60
    sec = total_sec % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{sec:02d}"
    return f"{minutes:02d}:{sec:02d}"

def parse_timestamp(timestamp_str: str) -> float:
    """Convert HH:MM:SS or MM:SS to seconds float."""
    parts = timestamp_str.strip().split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 1:
            return float(parts[0])
    except Exception:
        pass
    return 0.0
