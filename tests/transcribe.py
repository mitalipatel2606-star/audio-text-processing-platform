import sys
import os
from faster_whisper import WhisperModel

if len(sys.argv) < 2:
    print("Usage: python tests/transcribe.py <path_to_audio_file>")
    sys.exit(1)

audio_path = sys.argv[1]

if not os.path.exists(audio_path):
    print(f"Error: File '{audio_path}' does not exist.")
    sys.exit(1)

print("Loading Whisper model...")
model = WhisperModel("base", device="cpu", compute_type="int8")

print(f"Transcribing '{audio_path}'...")
segments, info = model.transcribe(audio_path)

print("\n--- Transcription Results ---")
has_output = False
for segment in segments:
    print(f"[{segment.start:.2f}s -> {segment.end:.2f}s]: {segment.text}")
    has_output = True

if not has_output:
    print("No speech detected.")
