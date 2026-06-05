import sounddevice as sd
import soundfile as sf
import os
import sys

AUDIO_DIR = "data/audio"
TRANSCRIPT_DIR = "data/transcripts"

os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

FS = 16000
DURATION = 5  # seconds

print("\n=== Benchmark Dataset Gathering Tool ===")
print("Use this tool to record voice samples and enter reference transcripts.")

while True:
    # Determine next audio index
    existing_files = [f for f in os.listdir(AUDIO_DIR) if f.startswith("audio") and f.endswith(".wav")]
    indices = [int(f[5:-4]) for f in existing_files if f[5:-4].isdigit()]
    sample_num = max(indices) + 1 if indices else 1
    
    print(f"\n--- Recording Sample #{sample_num} ---")
    transcript = input("Enter the EXACT text you will say (or type 'exit' to finish): ").strip()
    if transcript.lower() == 'exit':
        break
    if not transcript:
        print("Transcript cannot be empty. Please try again.")
        continue
        
    audio_path = os.path.join(AUDIO_DIR, f"audio{sample_num}.wav")
    transcript_path = os.path.join(TRANSCRIPT_DIR, f"audio{sample_num}.txt")
    
    print(f"Recording duration: {DURATION} seconds. Get ready...")
    input("Press Enter to start recording...")
    
    print("\n[RECORDING] Speak now...")
    try:
        recording = sd.rec(int(DURATION * FS), samplerate=FS, channels=1)
        sd.wait()
        print("[RECORDING COMPLETE]")
    except Exception as e:
        print(f"Error during recording: {e}", file=sys.stderr)
        continue
        
    # Save files
    sf.write(audio_path, recording, FS)
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(transcript)
        
    print(f"Saved:")
    print(f"  -> {audio_path}")
    print(f"  -> {transcript_path}")

print("\n=== Finished Gathering Dataset ===")
print(f"Your dataset is located in the 'data/' directory.")
