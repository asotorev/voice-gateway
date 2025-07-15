"""
Voice Gateway FastAPI Application.
Main application with DynamoDB integration and complete routing.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import healthcheck, auth


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Returns:
        FastAPI: Configured application instance
    """
    app = FastAPI(
        title="Voice Gateway API",
        version="0.1.0",
        description="Voice authentication system with DynamoDB persistence"
    )

    # Include route modules
    app.include_router(healthcheck.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    
    return app


app = create_app()