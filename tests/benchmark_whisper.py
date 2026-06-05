import os
import sys
import time
import wave
import re
from faster_whisper import WhisperModel

AUDIO_DIR = "data/audio"
TRANSCRIPT_DIR = "data/transcripts"

def get_audio_duration(file_path):
    """Returns the duration of a WAV file in seconds."""
    try:
        with wave.open(file_path, 'rb') as wav:
            frames = wav.getnframes()
            rate = wav.getframerate()
            duration = frames / float(rate)
            return duration
    except Exception as e:
        print(f"Error reading duration for {file_path}: {e}")
        return 0.0

def compute_wer(reference, hypothesis):
    """Computes Word Error Rate (WER) using Levenshtein distance."""
    def clean(text):
        # Convert to lowercase and remove punctuation
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        return text.split()

    ref_words = clean(reference)
    hyp_words = clean(hypothesis)
    
    # Levenshtein distance dynamic programming matrix
    d = [[0] * (len(hyp_words) + 1) for _ in range(len(ref_words) + 1)]
    for i in range(len(ref_words) + 1):
        d[i][0] = i
    for j in range(len(hyp_words) + 1):
        d[0][j] = j
        
    for i in range(1, len(ref_words) + 1):
        for j in range(1, len(hyp_words) + 1):
            if ref_words[i-1] == hyp_words[j-1]:
                d[i][j] = d[i-1][j-1]
            else:
                d[i][j] = min(
                    d[i-1][j] + 1,    # Deletion
                    d[i][j-1] + 1,    # Insertion
                    d[i-1][j-1] + 1   # Substitution
                )
    
    if not ref_words:
        return len(hyp_words)
    return d[len(ref_words)][len(hyp_words)] / len(ref_words)

def run_benchmark():
    if not os.path.exists(AUDIO_DIR) or not os.path.exists(TRANSCRIPT_DIR):
        print(f"Error: Missing data directories. Please ensure {AUDIO_DIR} and {TRANSCRIPT_DIR} exist.")
        sys.exit(1)

    # Find all WAV files
    audio_files = sorted([f for f in os.listdir(AUDIO_DIR) if f.endswith(".wav")])
    if not audio_files:
        print("No .wav files found in data/audio/.")
        print("Please record/add some samples first.")
        sys.exit(1)

    print(f"Found {len(audio_files)} audio samples for benchmarking.")

    models_to_test = ["tiny", "base", "small"]
    results = {}

    for model_name in models_to_test:
        print(f"\n==========================================")
        print(f"Benchmarking Model: {model_name.upper()}")
        print(f"==========================================")
        
        print(f"Loading {model_name} model...")
        try:
            model = WhisperModel(model_name, device="cpu", compute_type="int8")
        except Exception as e:
            print(f"Failed to load model '{model_name}': {e}")
            continue

        total_audio_duration_seconds = 0
        total_inference_time_seconds = 0
        wer_scores = []

        for audio_file in audio_files:
            audio_path = os.path.join(AUDIO_DIR, audio_file)
            base_name = os.path.splitext(audio_file)[0]
            transcript_path = os.path.join(TRANSCRIPT_DIR, f"{base_name}.txt")

            if not os.path.exists(transcript_path):
                print(f"Warning: Transcript file missing for {audio_file}. Skipping.")
                continue

            # Load reference transcript
            with open(transcript_path, "r", encoding="utf-8") as f:
                reference_text = f.read().strip()

            duration = get_audio_duration(audio_path)
            if duration == 0:
                continue

            total_audio_duration_seconds += duration

            # Transcribe and measure latency
            start_time = time.time()
            segments, info = model.transcribe(audio_path)
            # Exhaust generator to force full transcription
            transcribed_text = " ".join([segment.text for segment in segments]).strip()
            inference_time = time.time() - start_time

            total_inference_time_seconds += inference_time

            # Compute WER
            wer = compute_wer(reference_text, transcribed_text)
            wer_scores.append(wer)

            print(f"[{audio_file}] Duration: {duration:.2f}s | Processed in: {inference_time:.2f}s | WER: {wer:.2%}")
            print(f"  Ref : {reference_text}")
            print(f"  Hyp : {transcribed_text}")

        if total_audio_duration_seconds > 0:
            avg_latency = total_inference_time_seconds / (total_audio_duration_seconds / 60.0)
            avg_wer = sum(wer_scores) / len(wer_scores) if wer_scores else 0.0
            results[model_name] = {"latency": avg_latency, "wer": avg_wer}
        else:
            print("No valid audio duration recorded.")

    # Print Summary Table to stdout
    print("\n\n==========================================")
    print("           BENCHMARK RESULTS TABLE        ")
    print("==========================================")
    print(f"| {'Model':<10} | {'Latency (sec/min of audio)':<30} | {'WER (%)':<10} |")
    print(f"|{'-'*12}|{'-'*32}|{'-'*12}|")
    for model_name in models_to_test:
        if model_name in results:
            latency = f"{results[model_name]['latency']:.2f}s"
            wer = f"{results[model_name]['wer']:.2%}"
            print(f"| {model_name.capitalize():<10} | {latency:<30} | {wer:<10} |")
        else:
            print(f"| {model_name.capitalize():<10} | {'N/A':<30} | {'N/A':<10} |")
    print("==========================================\n")

    # Save Summary Table to a markdown file
    docs_dir = "docs"
    os.makedirs(docs_dir, exist_ok=True)
    report_path = os.path.join(docs_dir, "benchmark_results.md")
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Faster-Whisper Benchmarking Results\n\n")
        f.write(f"Evaluated on **{len(audio_files)}** audio samples.\n\n")
        f.write(f"| Model | Latency (sec/min of audio) | WER (%) |\n")
        f.write(f"| :--- | :--- | :--- |\n")
        for model_name in models_to_test:
            if model_name in results:
                latency = f"{results[model_name]['latency']:.2f}s"
                wer = f"{results[model_name]['wer']:.2%}"
                f.write(f"| **{model_name.capitalize()}** | {latency} | {wer} |\n")
            else:
                f.write(f"| **{model_name.capitalize()}** | N/A | N/A |\n")
                
    print(f"Benchmark results successfully stored in: {report_path}\n")

if __name__ == "__main__":
    run_benchmark()
