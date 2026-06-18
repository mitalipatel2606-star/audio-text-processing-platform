import io
import os
import wave
from typing import Dict
from piper.voice import PiperVoice

# Mapping of voice aliases to their model filenames in the workspace root.
VOICE_MAP = {
    "amy": "en_US-amy-medium.onnx",
    "danny": "en_US-danny-low.onnx",
    "joe": "en_US-joe-medium.onnx",
    "lessac": "en_US-lessac-medium.onnx",
    "ryan": "en_US-ryan-medium.onnx",
}

# Project root directory to locate the models
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Cache for loaded PiperVoice instances: maps voice_name (alias) -> PiperVoice
_loaded_voices: Dict[str, PiperVoice] = {}


def load_voice(voice_name: str) -> PiperVoice:
    """
    Loads the PiperVoice model for the given voice alias.
    Caches the loaded instance to avoid loading cost on subsequent calls.
    Raises ValueError if the voice alias is unknown.
    Raises FileNotFoundError if the voice model file is missing.
    """
    global _loaded_voices
    
    alias = voice_name.lower().strip()
    if alias not in VOICE_MAP:
        raise ValueError(
            f"Unknown voice alias '{voice_name}'. Supported aliases: {list(VOICE_MAP.keys())}"
        )
        
    if alias in _loaded_voices:
        return _loaded_voices[alias]
        
    model_filename = VOICE_MAP[alias]
    
    # Try project root first, then fall back to current working directory
    model_path = os.path.join(PROJECT_ROOT, model_filename)
    if not os.path.exists(model_path):
        model_path = os.path.join(os.getcwd(), model_filename)
        
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"Voice model file not found for alias '{voice_name}' (expected filename: '{model_filename}')"
        )
        
    print(f"Loading Piper voice '{voice_name}' from '{model_path}'...")
    voice = PiperVoice.load(model_path)
    print(f"Piper voice '{voice_name}' loaded successfully.")
    
    _loaded_voices[alias] = voice
    return voice


def synthesize(text: str, voice_name: str) -> bytes:
    """
    Synthesizes text into speech using the specified Piper voice alias.
    
    Parameters:
        text: The text to be spoken.
        voice_name: The voice alias (e.g. "amy", "lessac", "joe", "ryan", "danny").
        
    Returns:
        bytes: The synthesized WAV audio bytes.
    """
    voice = load_voice(voice_name)
    
    buf = io.BytesIO()
    # voice.synthesize_wav expects a wave.Wave_write instance
    with wave.open(buf, "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)
        
    return buf.getvalue()
