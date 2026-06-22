import os
import json
import math
import sys
import uuid
import time
import subprocess
import wave
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import Dict, List, Any
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query, Header, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import redis

# Ensure services directory is importable
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from services.stt.whisper_wrapper import transcribe as whisper_transcribe
from services.tts.piper_wrapper import synthesize, VOICE_MAP
from services.nlp.nlu_service import analyze_text

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm-load models concurrently
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor() as executor:
        futures = []
        
        # Warmup Whisper models
        def warm_whisper(model_size):
            from services.stt.whisper_wrapper import load_model
            try:
                load_model(model_size)
            except Exception as e:
                print(f"Error warm-loading Whisper {model_size}: {e}")
                
        # Warmup Piper voices
        def warm_piper_voice(voice_name):
            from services.tts.piper_wrapper import load_voice
            try:
                load_voice(voice_name)
            except Exception as e:
                print(f"Error warm-loading Piper voice {voice_name}: {e}")
                
        # We load 'base' as default, and 'tiny' since tests use it heavily
        futures.append(loop.run_in_executor(executor, warm_whisper, "base"))
        futures.append(loop.run_in_executor(executor, warm_whisper, "tiny"))
        
        for voice in VOICE_MAP.keys():
            futures.append(loop.run_in_executor(executor, warm_piper_voice, voice))
            
        await asyncio.gather(*futures)
    yield

app = FastAPI(title="STT and TTS Survey Evaluation Platform", lifespan=lifespan)

_redis_client = None

def get_redis_client():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        return None
        
    try:
        client = redis.Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=2.0)
        client.ping()
        _redis_client = client
        print(f"Connected to Redis at {redis_url}")
        return _redis_client
    except Exception as e:
        print(f"Warning: Redis connection attempt failed ({str(e)}). Using local file fallback.")
        return None

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

@app.get("/api/health")
def health_check():
    r_client = get_redis_client()
    redis_status = "disconnected"
    if r_client:
        try:
            r_client.ping()
            redis_status = "connected"
        except Exception:
            redis_status = "connection_failed"
            
    return {
        "status": "ok",
        "redis": redis_status,
        "responses_file_exists": os.path.exists(RESPONSES_PATH)
    }

@app.post("/api/submit-survey")
def submit_survey(submission: SurveySubmission):
    try:
        payload = submission.model_dump()
        
        # 1. Save to Redis if available
        r_client = get_redis_client()
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

@app.get("/api/results")
def get_survey_results():
    responses = []
    
    # Try fetching from Redis first
    r_client = get_redis_client()
    redis_loaded = False
    if r_client:
        try:
            raw_responses = r_client.lrange("survey_responses", 0, -1)
            if raw_responses:
                responses = [json.loads(r) for r in raw_responses]
                redis_loaded = True
                print(f"Loaded {len(responses)} responses from Redis.")
            else:
                # If Redis is empty but local file has data, sync local data into Redis
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

    # Fall back to file if Redis check didn't succeed or didn't fetch data
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

# Create a temp directory inside the project root for temporary uploads
TEMP_DIR = os.path.join(project_root, "backend", "temp_uploads")

def check_wav_format(file_path: str) -> bool:
    """Checks if the file is a 16kHz mono 16-bit PCM WAV."""
    try:
        with wave.open(file_path, "rb") as w:
            params = w.getparams()
            return (params.nchannels == 1 and 
                    params.sampwidth == 2 and 
                    params.framerate == 16000 and 
                    params.comptype == "NONE")
    except Exception:
        return False

def convert_audio_to_wav(input_path: str, output_path: str):
    """
    Converts any audio file format (MP3, WAV, WebM, FLAC, OGG, etc.)
    to a standardized 16kHz mono 16-bit PCM WAV using FFmpeg.
    """
    command = [
        "ffmpeg", "-y", "-i", input_path,
        "-ar", "16000",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        output_path
    ]
    try:
        # Run subprocess with timeout to prevent hang
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=30.0
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError("FFmpeg conversion timed out after 30 seconds.")
    except subprocess.CalledProcessError as e:
        stderr_msg = e.stderr.decode("utf-8", errors="ignore")
        raise RuntimeError(f"FFmpeg conversion failed: {stderr_msg}")

@app.post("/api/v1/stt")
async def transcribe_audio_endpoint(
    file: UploadFile = File(...),
    model: str = Form(None),
    language: str = Form(None),
    model_query: str = Query(None, alias="model"),
    language_query: str = Query(None, alias="language"),
    authorization: str = Header(None),
):
    # Optional Bearer Token Authentication
    expected_token = os.environ.get("STT_AUTH_TOKEN")
    if expected_token:
        if not authorization or authorization != f"Bearer {expected_token}":
            raise HTTPException(
                status_code=401,
                detail="Unauthorized: Invalid or missing authentication token"
            )

    selected_model = model or model_query
    selected_language = language or language_query
    
    # Ensure temporary upload directory exists
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    # Generate a unique path for the uploaded file inside the workspace
    file_extension = os.path.splitext(file.filename)[1] if file.filename else ""
    temp_file_name = f"{uuid.uuid4()}{file_extension}"
    temp_file_path = os.path.join(TEMP_DIR, temp_file_name)
    
    # Generate a path for the standardized converted WAV file
    converted_file_name = f"{uuid.uuid4()}_converted.wav"
    converted_file_path = os.path.join(TEMP_DIR, converted_file_name)
    
    try:
        # Write UploadFile to disk chunk-by-chunk to save memory
        with open(temp_file_path, "wb") as f:
            while content := await file.read(1024 * 1024):  # 1MB chunks
                f.write(content)
                
        # Check if the audio is already in the correct WAV format
        if check_wav_format(temp_file_path):
            converted_file_path = temp_file_path  # Skip conversion
        else:
            # Convert audio using ffmpeg to the expected format (16kHz mono 16-bit WAV)
            try:
                convert_audio_to_wav(temp_file_path, converted_file_path)
            except Exception as ce:
                raise HTTPException(status_code=400, detail=f"Audio conversion error: {str(ce)}")
            
        # Prepare optional transcription parameters
        transcribe_kwargs = {}
        if selected_language:
            # Strip whitespace and convert empty string to None
            lang_stripped = selected_language.strip()
            if lang_stripped:
                transcribe_kwargs["language"] = lang_stripped
                
        # Measure latency
        start_time = time.time()
        result = whisper_transcribe(
            audio_path=converted_file_path,
            model_size=selected_model,
            **transcribe_kwargs
        )
        latency = time.time() - start_time
        
        return {
            "text": result["text"],
            "language": result["metadata"]["language"],
            "duration": result["metadata"]["duration"],
            "latency": round(latency, 4)
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error during audio transcription: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    finally:
        # Securely clean up the temp files
        for path in [temp_file_path, converted_file_path]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as e:
                    print(f"Failed to clean up temp file {path}: {str(e)}")

def convert_audio_format(wav_bytes: bytes, target_format: str) -> bytes:
    """
    Converts standard WAV bytes to the requested format (mp3/ogg) on the fly
    using ffmpeg stdin/stdout piping.
    """
    target_format = target_format.lower().strip()
    if target_format == "wav":
        return wav_bytes
    
    if target_format not in ["mp3", "ogg"]:
        raise ValueError(f"Unsupported audio format: {target_format}")
    
    codec = "libmp3lame" if target_format == "mp3" else "libopus"
    
    command = [
        "ffmpeg", "-y",
        "-i", "pipe:0",
        "-acodec", codec,
        "-f", target_format,
        "pipe:1"
    ]
    try:
        result = subprocess.run(
            command,
            input=wav_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=30.0
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"FFmpeg conversion to {target_format} timed out.")
    except subprocess.CalledProcessError as e:
        stderr_msg = e.stderr.decode("utf-8", errors="ignore")
        raise RuntimeError(f"FFmpeg conversion to {target_format} failed: {stderr_msg}")

@app.post("/api/v1/tts")
async def text_to_speech_endpoint(
    request: Request,
    text: str = Form(None),
    voice: str = Form(None),
    format: str = Form(None),
    text_query: str = Query(None, alias="text"),
    voice_query: str = Query(None, alias="voice"),
    format_query: str = Query(None, alias="format"),
    authorization: str = Header(None),
):
    # Optional Bearer Token Authentication
    expected_token = os.environ.get("TTS_AUTH_TOKEN")
    if expected_token:
        if not authorization or authorization != f"Bearer {expected_token}":
            raise HTTPException(
                status_code=401,
                detail="Unauthorized: Invalid or missing authentication token"
            )

    # Resolve parameter values (order of preference: request body JSON/Form -> Query parameters)
    req_text = text
    req_voice = voice
    req_format = format

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
            if isinstance(body, dict):
                req_text = body.get("text", req_text)
                req_voice = body.get("voice", req_voice)
                req_format = body.get("format", req_format)
        except Exception:
            pass

    # Fallback to query parameters if still empty
    if not req_text:
        req_text = text_query
    if not req_voice:
        req_voice = voice_query
    if not req_format:
        req_format = format_query

    # Validate parameters
    # 1. Text validation
    if not req_text or not isinstance(req_text, str) or not req_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Bad Request: 'text' parameter is required and cannot be empty."
        )
    if len(req_text) > 5000:
        raise HTTPException(
            status_code=400,
            detail="Bad Request: 'text' parameter exceeds maximum length of 5000 characters."
        )

    # 2. Voice validation
    if not req_voice:
        raise HTTPException(
            status_code=400,
            detail="Bad Request: 'voice' parameter is required."
        )
    voice_lower = req_voice.lower().strip()
    if voice_lower not in VOICE_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Bad Request: Unknown voice alias '{req_voice}'. Supported voices: {list(VOICE_MAP.keys())}"
        )

    # 3. Format validation
    if not req_format:
        req_format = "wav"
    format_lower = req_format.lower().strip()
    if format_lower not in ["wav", "mp3", "ogg"]:
        raise HTTPException(
            status_code=400,
            detail=f"Bad Request: Unsupported format '{req_format}'. Supported formats: ['wav', 'mp3', 'ogg']"
        )

    # Determine media type
    if format_lower == "wav":
        media_type = "audio/wav"
    elif format_lower == "mp3":
        media_type = "audio/mpeg"
    else:
        media_type = "audio/ogg"

    import io
    try:
        # Synthesize audio using Piper
        wav_bytes = synthesize(req_text, voice_lower)
        
        # Convert audio format if needed
        audio_bytes = convert_audio_format(wav_bytes, format_lower)
        
        # Stream the audio response
        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type=media_type
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"Error during TTS synthesis: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"TTS synthesis/conversion failed: {str(e)}"
        )

@app.post("/api/v1/nlu")
async def nlu_endpoint(
    request: Request,
    text: str = Form(None),
    text_query: str = Query(None, alias="text"),
    authorization: str = Header(None),
):
    # Optional Bearer Token Authentication
    expected_token = os.environ.get("NLU_AUTH_TOKEN")
    if expected_token:
        if not authorization or authorization != f"Bearer {expected_token}":
            raise HTTPException(
                status_code=401,
                detail="Unauthorized: Invalid or missing authentication token"
            )

    # Resolve parameter values (order of preference: request body JSON/Form -> Query parameters)
    req_text = text

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
            if isinstance(body, dict):
                req_text = body.get("text", req_text)
        except Exception:
            pass

    # Fallback to query parameters if still empty
    if not req_text:
        req_text = text_query

    # Validate parameters
    # Text validation
    if not req_text or not isinstance(req_text, str) or not req_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Bad Request: 'text' parameter is required and cannot be empty."
        )

    try:
        # Run NLU analyze using services/nlp/nlu_service.py
        result = analyze_text(req_text)
        return result
    except Exception as e:
        print(f"Error during NLU parsing: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"NLU parsing failed: {str(e)}"
        )

# Mount static audio directories for direct serving
if os.path.exists(DATA_DIR):
    app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")

# Mount frontend client web app (served from /)
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    print(f"Warning: frontend directory '{FRONTEND_DIR}' does not exist yet. Please create it.")
