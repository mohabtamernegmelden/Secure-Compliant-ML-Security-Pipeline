from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config import settings

# Initialize slowapi Limiter with Redis backend or in-memory fallback
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],
    storage_uri=settings.REDIS_URL or "memory://"
)
