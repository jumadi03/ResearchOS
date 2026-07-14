from dotenv import load_dotenv
import os

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