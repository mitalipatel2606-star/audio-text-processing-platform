import os
import redis

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
