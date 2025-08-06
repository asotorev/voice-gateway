"""
Voice Gateway FastAPI Application (Clean Architecture).
Main application with database and storage integration and complete routing.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.audio import router as audio_router
from app.api.routes.healthcheck import router as healthcheck_router

from app.api.dependencies import validate_dependencies


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    """
    # Startup
    try:
        # Validate all dependencies can be created
        validate_dependencies()
        
        # Initialize infrastructure if needed
        await initialize_infrastructure()
        
    except Exception as e:
        raise
    
    yield


async def initialize_infrastructure():
    """
    Initialize infrastructure services if needed.
    
    """
    try:
        # Setup S3 buckets if needed 
        from app.infrastructure.storage.s3_setup import S3Setup
        s3_setup = S3Setup()
        
        bucket_results = s3_setup.setup_all_buckets()
        
    except Exception as e:
        # Don't fail startup - infrastructure can be set up manually
        pass


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application with Clean Architecture.
    
    """
    app = FastAPI(
        title="Voice Gateway API",
        version="2.0.0",
        description="Voice authentication system with Clean Architecture",
        lifespan=lifespan
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Route registration
    app.include_router(healthcheck_router, prefix="/api")
    app.include_router(auth_router, prefix="/api")
    app.include_router(audio_router, prefix="/api")
    
    return app


app = create_app()