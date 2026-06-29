import base64
import io
import os
import time
import uuid
from fastapi import APIRouter, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from backend import helpers
from backend.config import TEMP_DIR
from services.stt.whisper_wrapper import transcribe as whisper_transcribe
from services.tts.piper_wrapper import synthesize, VOICE_MAP
from services.nlp.nlu_service import analyze_text

router = APIRouter()

@router.post("/api/v1/stt")
async def transcribe_audio_endpoint(
    file: UploadFile = File(...),
    model: str = Form(None),
    language: str = Form(None),
    model_query: str = Query(None, alias="model"),
    language_query: str = Query(None, alias="language"),
    authorization: str = Header(None),
):
    expected_token = os.environ.get("STT_AUTH_TOKEN")
    if expected_token:
        if not authorization or authorization != f"Bearer {expected_token}":
            raise HTTPException(
                status_code=401,
                detail="Unauthorized: Invalid or missing authentication token"
            )

    selected_model = model or model_query
    selected_language = language or language_query
    
    os.makedirs(TEMP_DIR, exist_ok=True)
    file_extension = os.path.splitext(file.filename)[1] if file.filename else ""
    temp_file_name = f"{uuid.uuid4()}{file_extension}"
    temp_file_path = os.path.join(TEMP_DIR, temp_file_name)
    converted_file_name = f"{uuid.uuid4()}_converted.wav"
    converted_file_path = os.path.join(TEMP_DIR, converted_file_name)
    
    try:
        with open(temp_file_path, "wb") as f:
            while content := await file.read(1024 * 1024):
                f.write(content)
                
        if helpers.check_wav_format(temp_file_path):
            converted_file_path = temp_file_path
        else:
            try:
                helpers.convert_audio_to_wav(temp_file_path, converted_file_path)
            except Exception as ce:
                raise HTTPException(status_code=400, detail=f"Audio conversion error: {str(ce)}")
            
        transcribe_kwargs = {}
        if selected_language:
            lang_stripped = selected_language.strip()
            if lang_stripped:
                transcribe_kwargs["language"] = lang_stripped
                
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
        for path in [temp_file_path, converted_file_path]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as e:
                    print(f"Failed to clean up temp file {path}: {str(e)}")

@router.post("/api/v1/tts")
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
    expected_token = os.environ.get("TTS_AUTH_TOKEN")
    if expected_token:
        if not authorization or authorization != f"Bearer {expected_token}":
            raise HTTPException(
                status_code=401,
                detail="Unauthorized: Invalid or missing authentication token"
            )

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

    if not req_text:
        req_text = text_query
    if not req_voice:
        req_voice = voice_query
    if not req_format:
        req_format = format_query

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

    if not req_format:
        req_format = "wav"
    format_lower = req_format.lower().strip()
    if format_lower not in ["wav", "mp3", "ogg"]:
        raise HTTPException(
            status_code=400,
            detail=f"Bad Request: Unsupported format '{req_format}'. Supported formats: ['wav', 'mp3', 'ogg']"
        )

    if format_lower == "wav":
        media_type = "audio/wav"
    elif format_lower == "mp3":
        media_type = "audio/mpeg"
    else:
        media_type = "audio/ogg"

    try:
        wav_bytes = synthesize(req_text, voice_lower)
        audio_bytes = helpers.convert_audio_format(wav_bytes, format_lower)
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

@router.post("/api/v1/nlu")
async def nlu_endpoint(
    request: Request,
    text: str = Form(None),
    text_query: str = Query(None, alias="text"),
    authorization: str = Header(None),
):
    expected_token = os.environ.get("NLU_AUTH_TOKEN")
    if expected_token:
        if not authorization or authorization != f"Bearer {expected_token}":
            raise HTTPException(
                status_code=401,
                detail="Unauthorized: Invalid or missing authentication token"
            )

    req_text = text

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
            if isinstance(body, dict):
                req_text = body.get("text", req_text)
        except Exception:
            pass

    if not req_text:
        req_text = text_query

    if not req_text or not isinstance(req_text, str) or not req_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Bad Request: 'text' parameter is required and cannot be empty."
        )

    try:
        result = analyze_text(req_text)
        return result
    except Exception as e:
        print(f"Error during NLU parsing: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"NLU parsing failed: {str(e)}"
        )

@router.post("/api/v1/process")
async def process_audio_endpoint(
    file: UploadFile = File(...),
    tts_voice: str = Form("amy"),
    tts_format: str = Form("wav"),
    authorization: str = Header(None),
):
    expected_token = os.environ.get("PROCESS_AUTH_TOKEN")
    if expected_token:
        if not authorization or authorization != f"Bearer {expected_token}":
            raise HTTPException(
                status_code=401,
                detail="Unauthorized: Invalid or missing authentication token"
            )

    os.makedirs(TEMP_DIR, exist_ok=True)
    file_extension = os.path.splitext(file.filename)[1] if file.filename else ""
    temp_file_name = f"{uuid.uuid4()}{file_extension}"
    temp_file_path = os.path.join(TEMP_DIR, temp_file_name)
    converted_file_name = f"{uuid.uuid4()}_converted.wav"
    converted_file_path = os.path.join(TEMP_DIR, converted_file_name)

    try:
        with open(temp_file_path, "wb") as f:
            while content := await file.read(1024 * 1024):
                f.write(content)

        if helpers.check_wav_format(temp_file_path):
            converted_file_path = temp_file_path
        else:
            try:
                helpers.convert_audio_to_wav(temp_file_path, converted_file_path)
            except Exception as ce:
                raise HTTPException(status_code=400, detail=f"Audio conversion error: {str(ce)}")

        start_time = time.time()
        stt_result = whisper_transcribe(audio_path=converted_file_path)
        transcribed_text = stt_result["text"]

        nlu_result = analyze_text(transcribed_text)
        detected_intent = nlu_result["intent"]

        response_text = f"I heard you say: {transcribed_text}. The detected intent is {detected_intent}."
        
        voice_lower = tts_voice.lower().strip()
        if voice_lower not in VOICE_MAP:
            voice_lower = "amy"
            
        format_lower = tts_format.lower().strip()
        if format_lower not in ["wav", "mp3", "ogg"]:
            format_lower = "wav"
            
        wav_bytes = synthesize(response_text, voice_lower)
        audio_bytes = helpers.convert_audio_format(wav_bytes, format_lower)
        
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        latency = time.time() - start_time
        
        return {
            "input_text": transcribed_text,
            "nlu_data": nlu_result,
            "audio_response_base64": audio_base64,
            "audio_format": format_lower,
            "latency": round(latency, 4)
        }
    except Exception as e:
        print(f"Error during unified process: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Process failed: {str(e)}")
    finally:
        for path in set([temp_file_path, converted_file_path]):
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
