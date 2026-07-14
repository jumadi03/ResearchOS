from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.infrastructure.ai.ai_router import AIRouter
from app.models.chat import ChatRequest
from app.runtime.models.runtime_request import RuntimeRequest

router = APIRouter()

ai_router = AIRouter()


@router.post("/chat/stream")
def chat_stream(req: ChatRequest):

    runtime_request = RuntimeRequest(
        prompt=req.message,
        stream=True,
    )

    return StreamingResponse(
        ai_router.stream(
            runtime_request
        ),
        media_type="text/plain",
    )