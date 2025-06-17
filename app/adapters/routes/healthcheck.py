from fastapi import APIRouter

router = APIRouter()

@router.get("/ping", tags=["Health"])
async def ping():
    return {"message": "pong"}
