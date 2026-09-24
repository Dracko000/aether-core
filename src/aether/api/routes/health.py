from fastapi import APIRouter

from aether.config import settings

router = APIRouter()

@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "version": "0.1.0",
        "model": {
            "backend": "ollama",
            "default": settings.OLLAMA_MODEL,
            "base_url": settings.OLLAMA_BASE_URL,
        },
    }