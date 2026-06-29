import os
from fastapi import APIRouter
from backend import database as db
from backend.config import RESPONSES_PATH

router = APIRouter()

@router.get("/api/health")
def health_check():
    r_client = db.get_redis_client()
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
