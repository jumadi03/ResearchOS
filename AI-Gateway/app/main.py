from fastapi import FastAPI

from app.settings import APP_NAME
from app.settings import APP_VERSION

from app.router.chat import router as chat_router
from app.router.chat_stream import router as chat_stream_router
from app.router.chat_sse import router as chat_sse_router

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
)


@app.get("/")
def home():
    return {
        "message": "ResearchOS AI Gateway"
    }


app.include_router(chat_router)
app.include_router(chat_stream_router)
app.include_router(chat_sse_router)