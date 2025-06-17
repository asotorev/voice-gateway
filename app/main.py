from fastapi import FastAPI
from app.adapters.routes import healthcheck

def create_app() -> FastAPI:
    app = FastAPI(title="Voice Authentication API", version="0.1.0")

    app.include_router(healthcheck.router, prefix="/api")

    return app

app = create_app()
