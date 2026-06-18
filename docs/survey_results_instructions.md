# Instructions: Running the Survey & Adding New Audio Files

This guide outlines how to start the survey application, add new audio samples, and collect feedback from your 5–10 users.

---

## 1. How to Add More Audio Files

To include additional custom audio clips in the survey evaluation:

1. **Copy the Audio (.wav)**: Drop your `.wav` file into the `data/audio/` directory.
   - Example: `data/audio/my_evaluation_clip.wav`
2. **Create the Transcript (.txt)**: Create a text file with the **exact same name** in the `data/transcripts/` directory containing the reference transcript.
   - Example: `data/transcripts/my_evaluation_clip.txt` (inside, write the ground truth wording).
3. **Regenerate Survey Config**: Run the preparation script to automatically run Faster-Whisper (Tiny, Base, Small) over the new clips and update the survey metadata:
   ```bash
   python tests/prepare_survey_data.py
   ```

*Note: The script will automatically scan the `data/audio/` folder, find all `.wav` files, transcribe them, and write the updated mappings to `data/survey_data.json`.*

---

## 2. Setting Up & Running the Survey Application

### Step A: Install Backend Requirements
Install the required packages (`fastapi`, `uvicorn`, `pydantic`) in your Python environment:
```bash
pip install -r backend/requirements.txt
```

### Step B: Start the FastAPI Backend
Launch the FastAPI server on port 8000:
```bash
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```
- The backend serves REST API requests and handles static audio files.

### Step C: Start the React Frontend Client
Open a new terminal window, navigate to the `frontend/` folder, and launch the Vite dev server:
```bash
cd frontend
npm install
npm run dev
```
- The React client application will start at **`http://localhost:5173`**.

---

## 3. Gathering User Survey Results (MOS 1–5)

1. Invite your 5–10 users to navigate to the React client at **`http://localhost:5173`** (or your host IP if sharing across a local network).
2. Users enter their name/ID and go through the evaluation steps:
   - **Part 1: Text-to-Speech (TTS)**: Listen to Piper synthesis (Amy, Lessac, Joe, Ryan, Danny) and score on 1-5 scales.
   - **Part 2: Reference Audio Quality**: Listen to recorded clips and score their overall Clarity, Intelligibility, Noise level, and Overall Quality.
3. Click **Submit Survey** to save results. The responses are stored under `data/survey_responses.json`.

---

## 4. Viewing Analytics & Exporting Data

- Click the **Analytics Dashboard** button in the header of the React app.
- The dashboard dynamically queries the FastAPI server to fetch aggregated data:
  - Average Mean Opinion Score (MOS) per model/voice.
  - Standard Deviation (SD) measuring scoring consistency.
  - 95% Confidence Intervals (CI).
- Click **Export CSV** in the top-right corner of the dashboard to download a structured CSV spreadsheet (`survey_results.csv`) of raw results.
