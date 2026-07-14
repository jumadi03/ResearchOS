from fastapi import APIRouter
from sse_starlette import EventSourceResponse

from app.infrastructure.ai.transport.ollama_transport import OllamaTransport
from app.models.chat import ChatRequest

router = APIRouter()

transport = OllamaTransport()


@router.post("/chat/sse")
async def chat_sse(req: ChatRequest):

    async def event_generator():

        for token in transport.generate_stream(req.message):

            yield {
                "event": "token",
                "data": token,
            }

        yield {
            "event": "done",
            "data": "",
        }

    return EventSourceResponse(event_generator())