from fastapi import APIRouter

from app.infrastructure.ai.ai_router import AIRouter
from app.models.chat import ChatRequest
from app.runtime.models.runtime_request import RuntimeRequest

router = APIRouter()

ai_router = AIRouter()


@router.post("/chat")
def chat(req: ChatRequest):

    runtime_request = RuntimeRequest(
        prompt=req.message,
        stream=False,
    )

    answer = ai_router.execute(
        runtime_request
    )

    return {
        "question": req.message,
        "provider": answer.provider,
        "model": answer.model,
        "answer": answer.text,
    }