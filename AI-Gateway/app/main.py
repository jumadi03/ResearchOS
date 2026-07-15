from fastapi import FastAPI

from app.settings import APP_NAME
from app.settings import APP_VERSION

from app.router.chat import router as chat_router
from app.router.chat_stream import router as chat_stream_router
from app.router.chat_sse import router as chat_sse_router
from app.router.architecture import router as architecture_router
from app.architecture.pipeline_service import ArchitecturePipelineService
from app.settings import ARCHITECTURE_OUTPUT_ROOT, ARCHITECTURE_PROJECT_ROOT
from app.settings import ARCHITECTURE_API_PRINCIPALS
from app.architecture.authentication import BearerTokenAuthenticator
from app.observability import (
    AuditTrail,
    CorrelationMiddleware,
    MetricsRegistry,
    router as operations_router,
)

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
)

app.state.architecture_service = ArchitecturePipelineService(
    project_root=ARCHITECTURE_PROJECT_ROOT,
    output_root=ARCHITECTURE_OUTPUT_ROOT,
)
app.state.architecture_authenticator = BearerTokenAuthenticator(
    principals_by_token=ARCHITECTURE_API_PRINCIPALS,
)
app.state.metrics_registry = MetricsRegistry()
app.state.audit_trail = AuditTrail(
    ARCHITECTURE_OUTPUT_ROOT / "audit" / "security-publication.jsonl"
)
app.add_middleware(
    CorrelationMiddleware,
    metrics=app.state.metrics_registry,
)


@app.get("/")
def home():
    return {
        "message": "ResearchOS AI Gateway"
    }


app.include_router(chat_router)
app.include_router(chat_stream_router)
app.include_router(chat_sse_router)
app.include_router(architecture_router)
app.include_router(operations_router)
