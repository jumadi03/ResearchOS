import time

import requests
from fastapi import HTTPException

from app.infrastructure.ai.transport import (
    OllamaTransport,
    ResponseAssembler,
)

from app.logger import logger


_transport = OllamaTransport()


def ask_ollama(
    prompt: str,
) -> str:

    start_time = time.time()

    logger.info("=" * 60)
    logger.info("REQUEST START")
    logger.info(f"Prompt : {prompt}")

    try:

        data = _transport.generate(
            prompt,
        )

        answer = ResponseAssembler.assemble(
            data,
        )

        duration = round(
            time.time() - start_time,
            2,
        )

        logger.info(
            f"REQUEST SUCCESS ({duration}s)"
        )

        return answer

    except requests.exceptions.RequestException as exc:

        duration = round(
            time.time() - start_time,
            2,
        )

        logger.error(
            f"REQUEST FAILED ({duration}s)"
        )

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )