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
