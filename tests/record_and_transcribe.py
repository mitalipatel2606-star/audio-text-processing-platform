import sounddevice as sd
import soundfile as sf
from faster_whisper import WhisperModel
import sys

# Parameters
FS = 16000
DURATION = 5  # seconds
FILENAME = "user_sample.wav"

print("\n--- Speech-to-Text Microphone Test ---")
print(f"We will record {DURATION} seconds of audio.")
input("Press Enter to start recording...")

print("\n[RECORDING] Speak now...")
try:
    recording = sd.rec(int(DURATION * FS), samplerate=FS, channels=1)
    sd.wait()  # Wait until the recording is finished
    print("[RECORDING COMPLETE]")
except Exception as e:
    print(f"Error recording audio: {e}", file=sys.stderr)
    sys.exit(1)

# Save the recording
sf.write(FILENAME, recording, FS)
print(f"Saved audio to {FILENAME}")

# Run transcription
print("\nLoading Whisper model...")
model = WhisperModel("base", device="cpu", compute_type="int8")

print("Transcribing your recording...")
segments, info = model.transcribe(FILENAME)

print("\n--- Transcription Results ---")
has_output = False
for segment in segments:
    print(f"Transcribed Text: {segment.text}")
    has_output = True

if not has_output:
    print("No speech detected. Try speaking closer to the microphone or checking input settings.")
