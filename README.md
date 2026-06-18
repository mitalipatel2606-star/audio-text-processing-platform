# Audio-Text Processing Platform

A local speech-to-text (STT), text-to-speech (TTS), and natural language processing (NLP) evaluation and processing pipeline. 

This repository contains the boilerplate folders, local test utilities, benchmark dataset management, and evaluation results comparing different model weights.

---

## 1. Directory Structure

The project has been initialized with the following layout:

```text
audio-text-platform/
├── backend/            # Backend API service
├── data/               # Benchmark datasets
│   ├── audio/          # Reference audio voice notes (.wav)
│   └── transcripts/    # Reference transcript files (.txt)
├── docs/               # Documentation & benchmark reports
├── frontend/           # Frontend client application
├── services/           # Model loading & core pipeline logic
│   ├── nlp/            # NLP utilities (spaCy)
│   ├── stt/            # Speech-to-text pipeline (Whisper)
│   └── tts/            # Text-to-speech pipeline (Piper)
└── tests/              # Smoke test & benchmarking utilities
```

---

## 2. Installation & Prerequisites

This platform is configured to run models locally on macOS (support for Apple Silicon ARM64 is enabled).

```bash
# 1. Install core dependencies
pip install faster-whisper piper-tts spacy sounddevice soundfile numpy

# 2. Download the English NLP model
python -m spacy download en_core_web_sm
```

---

## 3. Smoke Test Verification Scripts

All testing utilities are located in the `tests/` directory:

### 🔊 Text-to-Speech (Piper)
Generate a synthetic audio note:
```bash
./tests/test_piper.sh
```
*Outputs: `test.wav`*

### 🎙️ Speech-to-Text (Faster-Whisper)
Transcribe the generated test audio:
```bash
python tests/test_whisper.py
```

### 🧠 Entity Extraction (spaCy)
Verify entity extraction:
```bash
python tests/test_spacy.py
```

---

## 4. Benchmark Dataset & Testing (W1-06 & W1-07)

### Step A: Gather Voice Clips
To compile the test dataset of 10-15 voice clips, you can record variable-length samples using:
```bash
python tests/gather_samples.py
```
- Press **Enter** to start recording.
- Speak and press **Enter** again to stop.
- The script automatically matches files and saves them to `data/audio/audioX.wav` and `data/transcripts/audioX.txt`.

### Step B: Run Whisper Benchmark
Evaluate Whisper **Tiny**, **Base**, and **Small** models on your dataset:
```bash
python tests/benchmark_whisper.py
```
This prints the comparison table and updates the report at [docs/benchmark_results.md](docs/benchmark_results.md).

---

## 5. Faster-Whisper Evaluation Results

The models were benchmarked on a dataset containing 11 audio clips (custom voice recordings + LJ Speech datasets) executing on CPU with `int8` quantization:

| Model | Latency (sec/min of audio) | WER (%) |
| :--- | :--- | :--- |
| **Tiny** | 5.04s | 20.74% |
| **Base** | 7.85s | 18.68% |
| **Small** | 21.24s | 17.33% |

- **Tiny** is optimized for high-speed local transcription but has higher error rates.
- **Base** offers the optimal compromise, providing high accuracy with minimal extra latency.
- **Small** delivers the lowest WER, but runs significantly slower on local CPU.
