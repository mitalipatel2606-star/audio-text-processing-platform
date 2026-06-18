import sounddevice as sd
import soundfile as sf
from faster_whisper import WhisperModel
import sys
import queue
import numpy as np

# Parameters
FS = 16000
CHANNELS = 1
FILENAME = "user_sample.wav"

print("\n--- Speech-to-Text Microphone Test (Variable Length) ---")
input("Press Enter to start recording...")

print("\n[RECORDING STARTED] Speak now...")
print(">>> Press ENTER to STOP recording <<<")

q = queue.Queue()

def callback(indata, frames, time, status):
    if status:
        print(status, file=sys.stderr)
    q.put(indata.copy())

try:
    with sd.InputStream(samplerate=FS, channels=CHANNELS, callback=callback):
        input()  # Wait for user to hit Enter to stop
    print("[RECORDING COMPLETE]")
except Exception as e:
    print(f"Error recording audio: {e}", file=sys.stderr)
    sys.exit(1)

# Collect audio data
data = []
while not q.empty():
    data.append(q.get())

if data:
    recording = np.concatenate(data, axis=0)
    sf.write(FILENAME, recording, FS)
    duration = len(recording) / FS
    print(f"Saved audio to {FILENAME} ({duration:.2f}s)")
else:
    print("No audio data was captured.")
    sys.exit(1)

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
