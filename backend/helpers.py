import math
import subprocess
import wave
from typing import Dict, List

def calculate_stats(scores: List[float]) -> Dict[str, float]:
    if not scores:
        return {"mean": 0.0, "std_dev": 0.0, "ci_margin": 0.0, "count": 0}
    n = len(scores)
    mean = sum(scores) / n
    if n > 1:
        variance = sum((x - mean) ** 2 for x in scores) / (n - 1)
        std_dev = math.sqrt(variance)
    else:
        std_dev = 0.0
    
    # 95% Confidence Interval: 1.96 * (std_dev / sqrt(n))
    sem = std_dev / math.sqrt(n) if n > 0 else 0.0
    ci_margin = 1.96 * sem
    
    return {
        "mean": round(mean, 2),
        "std_dev": round(std_dev, 2),
        "ci_margin": round(ci_margin, 2),
        "count": n
    }

def check_wav_format(file_path: str) -> bool:
    """Checks if the file is a 16kHz mono 16-bit PCM WAV."""
    try:
        with wave.open(file_path, "rb") as w:
            params = w.getparams()
            return (params.nchannels == 1 and 
                    params.sampwidth == 2 and 
                    params.framerate == 16000 and 
                    params.comptype == "NONE")
    except Exception:
        return False

def convert_audio_to_wav(input_path: str, output_path: str):
    """
    Converts any audio file format (MP3, WAV, WebM, FLAC, OGG, etc.)
    to a standardized 16kHz mono 16-bit PCM WAV using FFmpeg.
    """
    command = [
        "ffmpeg", "-y", "-i", input_path,
        "-ar", "16000",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        output_path
    ]
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=30.0
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError("FFmpeg conversion timed out after 30 seconds.")
    except subprocess.CalledProcessError as e:
        stderr_msg = e.stderr.decode("utf-8", errors="ignore")
        raise RuntimeError(f"FFmpeg conversion failed: {stderr_msg}")

def convert_audio_format(wav_bytes: bytes, target_format: str) -> bytes:
    """
    Converts standard WAV bytes to the requested format (mp3/ogg) on the fly
    using ffmpeg stdin/stdout piping.
    """
    target_format = target_format.lower().strip()
    if target_format == "wav":
        return wav_bytes
    
    if target_format not in ["mp3", "ogg"]:
        raise ValueError(f"Unsupported audio format: {target_format}")
    
    codec = "libmp3lame" if target_format == "mp3" else "libopus"
    
    command = [
        "ffmpeg", "-y",
        "-i", "pipe:0",
        "-acodec", codec,
        "-f", target_format,
        "pipe:1"
    ]
    try:
        result = subprocess.run(
            command,
            input=wav_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=30.0
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"FFmpeg conversion to {target_format} timed out.")
    except subprocess.CalledProcessError as e:
        stderr_msg = e.stderr.decode("utf-8", errors="ignore")
        raise RuntimeError(f"FFmpeg conversion to {target_format} failed: {stderr_msg}")
