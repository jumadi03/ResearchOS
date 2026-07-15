from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.settings import APP_NAME
from app.settings import APP_VERSION

from app.router.chat import router as chat_router, ai_router
from app.router.chat_stream import router as chat_stream_router
from app.router.chat_sse import router as chat_sse_router
from app.router.architecture import router as architecture_router
from app.router.knowledge import router as knowledge_router
from app.router.workspace import router as workspace_router
from app.router.session import router as session_router
from app.router.administration import router as administration_router
from app.product.sessions import WorkspaceSessionManager
from app.product.intelligence import IntelligenceLedger
from app.architecture.pipeline_service import ArchitecturePipelineService
from app.settings import ARCHITECTURE_OUTPUT_ROOT, ARCHITECTURE_PROJECT_ROOT
from app.settings import ARCHITECTURE_API_PRINCIPALS
from app.architecture.authentication import BearerTokenAuthenticator
from app.knowledge.authentication import KnowledgeAuthenticator
from app.knowledge.discovery.providers import (
    CrossrefProvider, OpenAlexProvider, SemanticScholarProvider,
)
from app.knowledge.service import KnowledgeDiscoveryService
from app.settings import (
    KNOWLEDGE_API_PRINCIPALS, KNOWLEDGE_OUTPUT_ROOT,
    KNOWLEDGE_PROVIDER_MAX_ATTEMPTS, KNOWLEDGE_PROVIDER_TIMEOUT,
    DATABASE_URL, KNOWLEDGE_DOCUMENT_MAX_BYTES, SEMANTIC_SCHOLAR_API_KEY,
    MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_DOCUMENT_BUCKET,
)
from app.knowledge.ingestion.acquisition import DocumentAcquirer
from app.knowledge.repositories.postgres import PostgresScientificDataRepository
from app.knowledge.repositories.minio import MinioScientificObjectStore
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
app.mount(
    "/workspace-assets",
    StaticFiles(directory=Path(__file__).resolve().parent / "product" / "static"),
    name="workspace-assets",
)
app.state.knowledge_authenticator = KnowledgeAuthenticator(KNOWLEDGE_API_PRINCIPALS)
app.state.workspace_sessions = WorkspaceSessionManager(DATABASE_URL) if DATABASE_URL else None
app.state.ai_router = ai_router
app.state.intelligence_ledger = IntelligenceLedger(DATABASE_URL) if DATABASE_URL else None
provider_options = {
    "timeout": KNOWLEDGE_PROVIDER_TIMEOUT,
    "max_attempts": KNOWLEDGE_PROVIDER_MAX_ATTEMPTS,
}
app.state.knowledge_service = KnowledgeDiscoveryService(
    (
        OpenAlexProvider(**provider_options),
        CrossrefProvider(**provider_options),
        SemanticScholarProvider(api_key=SEMANTIC_SCHOLAR_API_KEY, **provider_options),
    ),
    KNOWLEDGE_OUTPUT_ROOT,
    document_acquirer=DocumentAcquirer(max_bytes=KNOWLEDGE_DOCUMENT_MAX_BYTES),
    data_repository=(
        PostgresScientificDataRepository(DATABASE_URL) if DATABASE_URL else None
    ),
    object_store=(
        MinioScientificObjectStore(
            endpoint=MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY, bucket=MINIO_DOCUMENT_BUCKET,
        )
        if MINIO_ENDPOINT and MINIO_ACCESS_KEY and MINIO_SECRET_KEY else None
    ),
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
app.include_router(knowledge_router)
app.include_router(workspace_router)
app.include_router(session_router)
app.include_router(administration_router)
app.include_router(operations_router)
