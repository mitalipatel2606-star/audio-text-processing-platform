import os
import json
import math
from typing import Dict, List, Any
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="STT and TTS Survey Evaluation Platform")

# CORS middleware for testing flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
SURVEY_CONFIG_PATH = os.path.join(DATA_DIR, "survey_data.json")
RESPONSES_PATH = os.path.join(DATA_DIR, "survey_responses.json")

# Model definitions for Pydantic request validation
class UserInfo(BaseModel):
    name: str = Field(..., min_length=1)
    age: str = ""
    noise: str = ""

class TtsResponseItem(BaseModel):
    id: str
    voice: str
    naturalness: int = Field(..., ge=1, le=5)
    pronunciation: int = Field(..., ge=1, le=5)
    intonation: int = Field(..., ge=1, le=5)
    overall: int = Field(..., ge=1, le=5)

class SttResponseItem(BaseModel):
    id: str
    filename: str
    clarity: int = Field(..., ge=1, le=5)
    intelligibility: int = Field(..., ge=1, le=5)
    noise: int = Field(..., ge=1, le=5)
    overall: int = Field(..., ge=1, le=5)

class SurveySubmission(BaseModel):
    userInfo: UserInfo
    ttsResponses: List[TtsResponseItem]
    sttResponses: List[SttResponseItem]
    comments: str = ""

# Helper to compute statistics
def calculate_stats(scores: List[float]) -> Dict[str, float]:
    if not scores:
        return {"mean": 0.0, "std_dev": 0.0, "ci_margin": 0.0, "count": 0}
    n = len(scores)
    mean = sum(scores) / n
    if n > 1:
        variance = sum((x - mean) ** 2 for x in scores) / (n - 1)
        std_dev = math.sqrt(variance)
    else:
        std_dev = 0.0
    
    # 95% Confidence Interval: 1.96 * (std_dev / sqrt(n))
    sem = std_dev / math.sqrt(n) if n > 0 else 0.0
    ci_margin = 1.96 * sem
    
    return {
        "mean": round(mean, 2),
        "std_dev": round(std_dev, 2),
        "ci_margin": round(ci_margin, 2),
        "count": n
    }

@app.get("/api/survey-config")
def get_survey_config():
    if not os.path.exists(SURVEY_CONFIG_PATH):
        raise HTTPException(
            status_code=404, 
            detail="Survey data not prepared. Please run python tests/prepare_survey_data.py first."
        )
    try:
        with open(SURVEY_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading config: {str(e)}")

@app.post("/api/submit-survey")
def submit_survey(submission: SurveySubmission):
    try:
        responses = []
        if os.path.exists(RESPONSES_PATH):
            with open(RESPONSES_PATH, "r", encoding="utf-8") as f:
                try:
                    responses = json.load(f)
                    if not isinstance(responses, list):
                        responses = []
                except json.JSONDecodeError:
                    responses = []

        responses.append(submission.model_dump())
        
        with open(RESPONSES_PATH, "w", encoding="utf-8") as f:
            json.dump(responses, f, indent=2)
            
        return {"status": "success", "message": "Survey submitted successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving survey response: {str(e)}")

@app.get("/api/results")
def get_survey_results():
    if not os.path.exists(RESPONSES_PATH):
        return {
            "summary": {"tts": {}, "stt": {}},
            "total_submissions": 0,
            "raw_responses": []
        }

    try:
        with open(RESPONSES_PATH, "r", encoding="utf-8") as f:
            responses = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading responses: {str(e)}")

    # Group scores by model
    tts_scores: Dict[str, Dict[str, List[int]]] = {}
    stt_scores: Dict[str, Dict[str, List[int]]] = {}

    for resp in responses:
        # TTS
        for item in resp.get("ttsResponses", []):
            voice = item["voice"]
            if voice not in tts_scores:
                tts_scores[voice] = {"naturalness": [], "pronunciation": [], "intonation": [], "overall": []}
            tts_scores[voice]["naturalness"].append(item["naturalness"])
            tts_scores[voice]["pronunciation"].append(item["pronunciation"])
            tts_scores[voice]["intonation"].append(item["intonation"])
            tts_scores[voice]["overall"].append(item["overall"])

        # STT (Reference Audio Quality)
        for item in resp.get("sttResponses", []):
            filename = item["filename"]
            if filename not in stt_scores:
                stt_scores[filename] = {"clarity": [], "intelligibility": [], "noise": [], "overall": []}
            stt_scores[filename]["clarity"].append(item["clarity"])
            stt_scores[filename]["intelligibility"].append(item["intelligibility"])
            stt_scores[filename]["noise"].append(item["noise"])
            stt_scores[filename]["overall"].append(item["overall"])

    # Aggregate stats
    tts_summary = {}
    for voice, categories in tts_scores.items():
        tts_summary[voice] = {
            cat: calculate_stats(scores) for cat, scores in categories.items()
        }

    stt_summary = {}
    for filename, categories in stt_scores.items():
        stt_summary[filename] = {
            cat: calculate_stats(scores) for cat, scores in categories.items()
        }

    return {
        "summary": {
            "tts": tts_summary,
            "stt": stt_summary
        },
        "total_submissions": len(responses),
        "raw_responses": responses
    }

# Mount static audio directories for direct serving
if os.path.exists(DATA_DIR):
    app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")

# Mount frontend client web app (served from /)
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    print(f"Warning: frontend directory '{FRONTEND_DIR}' does not exist yet. Please create it.")
