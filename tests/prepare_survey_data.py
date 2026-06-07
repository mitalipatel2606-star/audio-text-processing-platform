import os
import json
import sys

# Paths
AUDIO_DIR = "data/audio"
TRANSCRIPT_DIR = "data/transcripts"
GENERATED_DIR = "data/generated_samples"
OUTPUT_JSON = "data/survey_data.json"

# TTS Texts and Voices
TTS_TEXTS = [
    "Welcome to the local speech evaluation pipeline.",
    "Your audio has been successfully transcribed into text.",
    "Synthesizing high-quality natural voice notes for testing purposes.",
    "Evaluating speech-to-text accuracy and response latency on local hardware.",
    "This is a product demonstration of local Piper text-to-speech synthesis."
]

TTS_VOICES = {
    "Amy (Medium)": "Amy_Medium",
    "Lessac (Medium)": "Lessac_Medium",
    "Joe (Medium)": "Joe_Medium",
    "Ryan (Medium)": "Ryan_Medium",
    "Danny (Low)": "Danny_Low"
}

def main():
    print("==========================================")
    print("  PREPARING SIMPLIFIED SURVEY DATASET     ")
    print("==========================================\n")

    # 1. Package TTS Data
    print("Processing Text-to-Speech (TTS) samples...")
    tts_data = []
    for idx, text in enumerate(TTS_TEXTS):
        sample_num = idx + 1
        voice_evals = []
        for voice_name, file_prefix in TTS_VOICES.items():
            filename = f"{file_prefix}_sample{sample_num}.wav"
            file_path = os.path.join(GENERATED_DIR, filename)
            
            if os.path.exists(file_path):
                voice_evals.append({
                    "voice": voice_name,
                    "audio_path": f"/data/generated_samples/{filename}"
                })
            else:
                print(f"  Warning: Missing TTS file: {file_path}")

        if voice_evals:
            tts_data.append({
                "id": f"tts_{sample_num}",
                "text": text,
                "voice_evals": voice_evals
            })

    # 2. Package STT / Audio Quality Data
    print("\nProcessing Audio Quality samples...")
    stt_data = []
    
    if not os.path.exists(AUDIO_DIR) or not os.path.exists(TRANSCRIPT_DIR):
        print(f"Error: missing directories {AUDIO_DIR} or {TRANSCRIPT_DIR}")
        sys.exit(1)

    audio_files = sorted([f for f in os.listdir(AUDIO_DIR) if f.endswith(".wav")])
    if not audio_files:
        print("No reference wave files found in data/audio/.")
        sys.exit(1)

    print(f"Found {len(audio_files)} reference audio files.")

    for file_idx, audio_file in enumerate(audio_files):
        audio_path = os.path.join(AUDIO_DIR, audio_file)
        base_name = os.path.splitext(audio_file)[0]
        transcript_path = os.path.join(TRANSCRIPT_DIR, f"{base_name}.txt")

        # Load reference text if present, otherwise default to empty
        reference_text = ""
        if os.path.exists(transcript_path):
            with open(transcript_path, "r", encoding="utf-8") as f:
                reference_text = f.read().strip()

        stt_data.append({
            "id": f"audio_{file_idx + 1}",
            "filename": audio_file,
            "audio_path": f"/data/audio/{audio_file}",
            "reference_text": reference_text
        })

    # 3. Write output JSON
    survey_dataset = {
        "tts": tts_data,
        "stt": stt_data
    }

    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(survey_dataset, f, indent=2)

    print(f"\nSuccess! Survey dataset written to {OUTPUT_JSON}")
    print(f"TTS Tasks: {len(tts_data)} | Audio Tasks: {len(stt_data)}")

if __name__ == "__main__":
    main()
