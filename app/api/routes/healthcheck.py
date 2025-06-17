from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("/ping")
async def ping():
    return {"message": "pong"}