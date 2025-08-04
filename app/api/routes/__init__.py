"""
API routes module.
Contains FastAPI route definitions.
"""

# Export all routers for easy import in main.py
from .healthcheck import router as healthcheck_router
from .auth import router as auth_router
from .audio import router as audio_router

__all__ = ["healthcheck_router", "auth_router", "audio_router"] 