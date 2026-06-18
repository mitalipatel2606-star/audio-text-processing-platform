from faster_whisper import WhisperModel

print("Loading Whisper model...")
model = WhisperModel("base", device="cpu", compute_type="int8")

print("Transcribing test.wav...")
segments, info = model.transcribe("test.wav")

print("Transcription results:")
for segment in segments:
    print(segment.text)
