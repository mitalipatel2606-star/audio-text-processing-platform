import asyncio
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Ensure services directory is importable
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from services.tts.piper_wrapper import VOICE_MAP
from backend.config import DATA_DIR, FRONTEND_DIR
from backend import database as db
from backend.routers import health, survey, services

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

# Expose database client at backend.main namespace for test backward-compatibility
get_redis_client = db.get_redis_client

# CORS middleware for testing flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include sub-routers
app.include_router(health.router)
app.include_router(survey.router)
app.include_router(services.router)

# Mount static audio directories for direct serving
if os.path.exists(DATA_DIR):
    app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")

# Mount frontend client web app (served from /)
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    print(f"Warning: frontend directory '{FRONTEND_DIR}' does not exist yet. Please create it.")
