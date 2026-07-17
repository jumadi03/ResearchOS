from dotenv import load_dotenv
import os
from pathlib import Path
import json

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "ResearchOS API")

APP_VERSION = os.getenv("APP_VERSION", "0.4.0")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")

MODEL_NAME = os.getenv("MODEL_NAME", "qwen3:8b")

#
# HTTP Transport Timeout
#

CONNECT_TIMEOUT = int(
    os.getenv("CONNECT_TIMEOUT", 5)
)

READ_TIMEOUT = int(
    os.getenv("READ_TIMEOUT", 120)
)

#
# Legacy configuration
# Dipertahankan sementara selama masa migrasi.
#

TIMEOUT = int(
    os.getenv("TIMEOUT", 60)
)

PROJECT_DIRECTORY = Path(__file__).resolve().parents[1]
ARCHITECTURE_PROJECT_ROOT = Path(
    os.getenv("ARCHITECTURE_PROJECT_ROOT", str(PROJECT_DIRECTORY))
)
ARCHITECTURE_OUTPUT_ROOT = Path(
    os.getenv(
        "ARCHITECTURE_OUTPUT_ROOT",
        str(PROJECT_DIRECTORY / "output" / "architecture"),
    )
)
def _principal_mapping(variable: str) -> dict:
    raw = os.getenv(variable, "{}")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{variable} must contain valid JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{variable} must contain a JSON object")
    return value


ARCHITECTURE_API_PRINCIPALS = _principal_mapping("ARCHITECTURE_API_PRINCIPALS")

KNOWLEDGE_OUTPUT_ROOT = Path(
    os.getenv("KNOWLEDGE_OUTPUT_ROOT", str(PROJECT_DIRECTORY / "output" / "knowledge"))
)
KNOWLEDGE_API_PRINCIPALS = _principal_mapping("KNOWLEDGE_API_PRINCIPALS")
SEMANTIC_SCHOLAR_API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
KNOWLEDGE_PROVIDER_TIMEOUT = float(os.getenv("KNOWLEDGE_PROVIDER_TIMEOUT", "20"))
KNOWLEDGE_PROVIDER_MAX_ATTEMPTS = int(os.getenv("KNOWLEDGE_PROVIDER_MAX_ATTEMPTS", "3"))
KNOWLEDGE_DOCUMENT_MAX_BYTES = int(os.getenv("KNOWLEDGE_DOCUMENT_MAX_BYTES", "25000000"))
DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_SCHEMA_VERSION = int(os.getenv("DATABASE_SCHEMA_VERSION", "20"))
READINESS_WORKER_MAX_AGE_SECONDS = int(
    os.getenv("READINESS_WORKER_MAX_AGE_SECONDS", "15")
)
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY") or os.getenv("MINIO_ROOT_USER")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY") or os.getenv("MINIO_ROOT_PASSWORD")
MINIO_DOCUMENT_BUCKET = os.getenv("MINIO_DOCUMENT_BUCKET", "researchos-documents")


def validate_runtime_configuration() -> None:
    if CONNECT_TIMEOUT <= 0 or READ_TIMEOUT <= 0 or TIMEOUT <= 0:
        raise RuntimeError("HTTP timeout values must be positive")
    if KNOWLEDGE_PROVIDER_TIMEOUT <= 0 or KNOWLEDGE_PROVIDER_MAX_ATTEMPTS <= 0:
        raise RuntimeError("Knowledge provider timeout and attempts must be positive")
    if KNOWLEDGE_DOCUMENT_MAX_BYTES <= 0:
        raise RuntimeError("KNOWLEDGE_DOCUMENT_MAX_BYTES must be positive")
    if READINESS_WORKER_MAX_AGE_SECONDS <= 0:
        raise RuntimeError("READINESS_WORKER_MAX_AGE_SECONDS must be positive")
    minio_values = (MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY)
    if any(minio_values) and not all(minio_values):
        raise RuntimeError(
            "MINIO_ENDPOINT, MINIO_ACCESS_KEY, and MINIO_SECRET_KEY must be configured together"
        )
