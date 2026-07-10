from fastapi import APIRouter, HTTPException

from app.exceptions import ExternalProviderError
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import chat_service


router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    session_id = request.session_id or "default"
    try:
        reply, debug = await chat_service.chat(request.message, session_id)
    except ExternalProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return ChatResponse(reply=reply, debug=debug)
