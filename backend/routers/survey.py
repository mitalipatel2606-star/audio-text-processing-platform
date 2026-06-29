import json
import os
from typing import Dict, List
from fastapi import APIRouter, HTTPException
from backend import database as db
from backend import models
from backend import helpers
from backend.config import SURVEY_CONFIG_PATH, RESPONSES_PATH

router = APIRouter()

@router.get("/api/survey-config")
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

@router.post("/api/submit-survey")
def submit_survey(submission: models.SurveySubmission):
    try:
        payload = submission.model_dump()
        
        # 1. Save to Redis if available
        r_client = db.get_redis_client()
        redis_saved = False
        if r_client:
            try:
                r_client.rpush("survey_responses", json.dumps(payload))
                redis_saved = True
                print("Response saved to Redis.")
            except Exception as re:
                print(f"Failed to write to Redis: {str(re)}")

        # 2. Save to local JSON file for persistence/fallback
        responses = []
        if os.path.exists(RESPONSES_PATH):
            with open(RESPONSES_PATH, "r", encoding="utf-8") as f:
                try:
                    responses = json.load(f)
                    if not isinstance(responses, list):
                        responses = []
                except json.JSONDecodeError:
                    responses = []

        responses.append(payload)
        
        with open(RESPONSES_PATH, "w", encoding="utf-8") as f:
            json.dump(responses, f, indent=2)
            
        status_msg = "Survey submitted successfully!"
        if redis_saved:
            status_msg += " (Saved to Redis & Disk)"
        else:
            status_msg += " (Saved to Disk)"
            
        return {"status": "success", "message": status_msg}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving survey response: {str(e)}")

@router.get("/api/results")
def get_survey_results():
    responses = []
    
    # Try fetching from Redis first
    r_client = db.get_redis_client()
    redis_loaded = False
    if r_client:
        try:
            raw_responses = r_client.lrange("survey_responses", 0, -1)
            if raw_responses:
                responses = [json.loads(r) for r in raw_responses]
                redis_loaded = True
                print(f"Loaded {len(responses)} responses from Redis.")
            else:
                # Sync local data into Redis
                if os.path.exists(RESPONSES_PATH):
                    with open(RESPONSES_PATH, "r", encoding="utf-8") as f:
                        try:
                            responses = json.load(f)
                            if not isinstance(responses, list):
                                responses = []
                        except json.JSONDecodeError:
                            responses = []
                    
                    if responses:
                        print(f"Syncing {len(responses)} local responses to Redis.")
                        for resp in responses:
                            r_client.rpush("survey_responses", json.dumps(resp))
                        redis_loaded = True
        except Exception as re:
            print(f"Failed to read from/sync to Redis: {str(re)}")

    # Fall back to file
    if not redis_loaded:
        if os.path.exists(RESPONSES_PATH):
            try:
                with open(RESPONSES_PATH, "r", encoding="utf-8") as f:
                    responses = json.load(f)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error reading responses: {str(e)}")
        else:
            responses = []

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

        # STT
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
            cat: helpers.calculate_stats(scores) for cat, scores in categories.items()
        }

    stt_summary = {}
    for filename, categories in stt_scores.items():
        stt_summary[filename] = {
            cat: helpers.calculate_stats(scores) for cat, scores in categories.items()
        }

    return {
        "summary": {
            "tts": tts_summary,
            "stt": stt_summary
        },
        "total_submissions": len(responses),
        "raw_responses": responses
    }
