import os
from typing import Dict, Any, List
from faster_whisper import WhisperModel

# Retrieve configuration from environment variables or defaults
DEFAULT_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")
DEFAULT_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
DEFAULT_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

class WhisperWrapper:
    def __init__(self, model_size: str = DEFAULT_MODEL_SIZE, device: str = DEFAULT_DEVICE, compute_type: str = DEFAULT_COMPUTE_TYPE):
        """
        Initializes and loads the Faster-Whisper model.
        """
        print(f"Loading Whisper model '{model_size}' on device '{device}' with '{compute_type}'...")
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        print("Whisper model loaded successfully.")

    def transcribe(self, audio_path: str, **kwargs) -> Dict[str, Any]:
        """
        Transcribes the given audio file.
        Returns a dictionary containing:
            - "text": The complete transcription text.
            - "metadata": A dictionary with details such as language, probability, duration, and segment info.
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        segments, info = self.model.transcribe(audio_path, **kwargs)

        # Collect segment data and exhaust generator to force completion of transcription
        segment_list = []
        text_parts = []
        for segment in segments:
            text_parts.append(segment.text)
            segment_list.append({
                "start": round(segment.start, 2),
                "end": round(segment.end, 2),
                "text": segment.text.strip(),
                "avg_logprob": round(segment.avg_logprob, 4),
                "no_speech_prob": round(segment.no_speech_prob, 4)
            })

        full_text = " ".join(text_parts).strip()

        metadata = {
            "language": info.language,
            "language_probability": round(info.language_probability, 4),
            "duration": round(info.duration, 2),
            "duration_after_vad": round(info.duration_after_vad, 2),
            "segments": segment_list
        }

        return {
            "text": full_text,
            "metadata": metadata
        }

# Global models cache mapping model_size to WhisperWrapper instance
_model_instances: Dict[str, WhisperWrapper] = {}
_model_instance = None # kept for backward compatibility

def load_model(model_size: str = DEFAULT_MODEL_SIZE, device: str = DEFAULT_DEVICE, compute_type: str = DEFAULT_COMPUTE_TYPE) -> WhisperWrapper:
    """
    Explicitly loads the Whisper model instance into memory and caches it.
    """
    global _model_instance, _model_instances
    if model_size not in _model_instances:
        _model_instances[model_size] = WhisperWrapper(model_size=model_size, device=device, compute_type=compute_type)
    
    # Maintain backward compatibility for single _model_instance global variable
    if model_size == DEFAULT_MODEL_SIZE or _model_instance is None:
        _model_instance = _model_instances[model_size]
        
    return _model_instances[model_size]

def transcribe(audio_path: str, model_size: str = None, **kwargs) -> Dict[str, Any]:
    """
    Unit-callable function to transcribe an audio file.
    Ensures the model of the specified size is loaded on demand if not already loaded.
    """
    global _model_instances
    if model_size is None:
        model_size = DEFAULT_MODEL_SIZE
        
    if model_size not in _model_instances:
        load_model(model_size=model_size)
        
    return _model_instances[model_size].transcribe(audio_path, **kwargs)
