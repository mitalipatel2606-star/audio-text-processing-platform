import os
import sys
import time
import wave
import subprocess

# Voices to benchmark
VOICES = {
    "Amy (Medium)": "en_US-amy-medium.onnx",
    "Lessac (Medium)": "en_US-lessac-medium.onnx",
    "Joe (Medium)": "en_US-joe-medium.onnx",
    "Ryan (Medium)": "en_US-ryan-medium.onnx",
    "Danny (Low)": "en_US-danny-low.onnx"
}

# Real product text samples
TEXTS = [
    "Welcome to the local speech evaluation pipeline.",
    "Your audio has been successfully transcribed into text.",
    "Synthesizing high-quality natural voice notes for testing purposes.",
    "Evaluating speech-to-text accuracy and response latency on local hardware.",
    "This is a product demonstration of local Piper text-to-speech synthesis."
]

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

def run_benchmark():
    # Verify all models exist
    missing_models = []
    for name, model_file in VOICES.items():
        if not os.path.exists(model_file):
            missing_models.append(model_file)
            
    if missing_models:
        print(f"Error: Missing model files: {missing_models}")
        sys.exit(1)

    output_dir = "data/generated_samples"
    os.makedirs(output_dir, exist_ok=True)

    results = {}

    print("\n==========================================")
    print("      BENCHMARKING PIPER TTS VOICES       ")
    print("==========================================\n")

    for name, model_file in VOICES.items():
        print(f"Testing Voice: {name} ({model_file})...")
        
        rtf_scores = []
        durations = []
        process_times = []

        for idx, text in enumerate(TEXTS):
            output_file = os.path.join(output_dir, f"{name.replace(' ', '_').replace('(', '').replace(')', '')}_sample{idx+1}.wav")
            
            # Start timer
            start_time = time.time()
            
            # Run piper command via shell
            try:
                process = subprocess.Popen(
                    ["piper", "--model", model_file, "--output_file", output_file],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                stdout, stderr = process.communicate(input=text)
                
                if process.returncode != 0:
                    print(f"  Error generating text {idx+1}: {stderr}")
                    continue
            except Exception as e:
                print(f"  Failed to run piper: {e}")
                continue
                
            processing_time = time.time() - start_time
            duration = get_audio_duration(output_file)
            
            if duration > 0:
                rtf = processing_time / duration
                rtf_scores.append(rtf)
                durations.append(duration)
                process_times.append(processing_time)
                print(f"  [Sample {idx+1}] Text len: {len(text)} chars | Duration: {duration:.2f}s | CPU Process: {processing_time:.2f}s | RTF: {rtf:.3f}")
            else:
                print(f"  [Sample {idx+1}] Duration calculation failed.")

        if rtf_scores:
            avg_rtf = sum(rtf_scores) / len(rtf_scores)
            results[name] = {
                "rtf": avg_rtf,
                "duration": sum(durations),
                "process_time": sum(process_times)
            }
            print(f"  -> Average Real-Time Factor (RTF): {avg_rtf:.3f}\n")
        else:
            print(f"  -> Failed to obtain valid results for {name}\n")

    # Print markdown table to console
    print("\n==========================================")
    print("           PIPER TTS RESULTS TABLE        ")
    print("==========================================")
    print(f"| {'Voice Model':<20} | {'Total Duration':<15} | {'Total CPU Time':<15} | {'RTF (Avg)':<10} |")
    print(f"|{'-'*22}|{'-'*17}|{'-'*17}|{'-'*12}|")
    for name in VOICES:
        if name in results:
            dur = f"{results[name]['duration']:.2f}s"
            proc = f"{results[name]['process_time']:.2f}s"
            rtf = f"{results[name]['rtf']:.3f}"
            print(f"| {name:<20} | {dur:<15} | {proc:<15} | {rtf:<10} |")
        else:
            print(f"| {name:<20} | {'N/A':<15} | {'N/A':<15} | {'N/A':<10} |")
    print("==========================================\n")

    # Save to docs/piper_results.md
    docs_dir = "docs"
    os.makedirs(docs_dir, exist_ok=True)
    report_path = os.path.join(docs_dir, "piper_results.md")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Piper TTS Voice Benchmarking Results\n\n")
        f.write(f"Evaluated on **{len(TEXTS)}** product text phrases.\n\n")
        f.write(f"| Voice Model | Total Audio Duration | Total CPU Synthesis Time | Average RTF |\n")
        f.write(f"| :--- | :--- | :--- | :--- |\n")
        for name in VOICES:
            if name in results:
                dur = f"{results[name]['duration']:.2f}s"
                proc = f"{results[name]['process_time']:.2f}s"
                rtf = f"{results[name]['rtf']:.3f}"
                f.write(f"| **{name}** | {dur} | {proc} | **{rtf}** |\n")
            else:
                f.write(f"| **{name}** | N/A | N/A | N/A |\n")

    print(f"Results successfully saved to: {report_path}\n")

if __name__ == "__main__":
    run_benchmark()
