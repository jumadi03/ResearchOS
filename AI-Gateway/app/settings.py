from dotenv import load_dotenv
import os
from pathlib import Path
import json

load_dotenv()

APP_NAME = os.getenv("APP_NAME")

APP_VERSION = os.getenv("APP_VERSION")

OLLAMA_URL = os.getenv("OLLAMA_URL")

MODEL_NAME = os.getenv("MODEL_NAME")

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
ARCHITECTURE_API_PRINCIPALS = json.loads(
    os.getenv("ARCHITECTURE_API_PRINCIPALS", "{}")
)

KNOWLEDGE_OUTPUT_ROOT = Path(
    os.getenv("KNOWLEDGE_OUTPUT_ROOT", str(PROJECT_DIRECTORY / "output" / "knowledge"))
)
KNOWLEDGE_API_PRINCIPALS = json.loads(os.getenv("KNOWLEDGE_API_PRINCIPALS", "{}"))
SEMANTIC_SCHOLAR_API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
KNOWLEDGE_PROVIDER_TIMEOUT = float(os.getenv("KNOWLEDGE_PROVIDER_TIMEOUT", "20"))
KNOWLEDGE_PROVIDER_MAX_ATTEMPTS = int(os.getenv("KNOWLEDGE_PROVIDER_MAX_ATTEMPTS", "3"))
KNOWLEDGE_DOCUMENT_MAX_BYTES = int(os.getenv("KNOWLEDGE_DOCUMENT_MAX_BYTES", "25000000"))
DATABASE_URL = os.getenv("DATABASE_URL")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY") or os.getenv("MINIO_ROOT_USER")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY") or os.getenv("MINIO_ROOT_PASSWORD")
MINIO_DOCUMENT_BUCKET = os.getenv("MINIO_DOCUMENT_BUCKET", "researchos-documents")
