"""
Voice Gateway FastAPI Application.
Main application with DynamoDB integration and complete routing.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import healthcheck, auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup events.
    """
    # Startup
    try:
        from app.infrastructure.storage.s3_setup import S3Setup
        # Setup S3 buckets if needed
        s3_setup = S3Setup()
        results = s3_setup.setup_all_buckets()
    except Exception as e:
        pass
        # Don't fail startup - buckets can be created manually
    yield


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Returns:
        FastAPI: Configured application instance
    """
    app = FastAPI(
        title="Voice Gateway API",
        version="0.1.0",
        description="Voice authentication system with DynamoDB persistence",
        lifespan=lifespan
    )

    # Include route modules
    app.include_router(healthcheck.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    
    return app


app = create_app()