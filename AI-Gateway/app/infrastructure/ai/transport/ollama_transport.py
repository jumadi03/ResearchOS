import json

import requests

from app.settings import (
    CONNECT_TIMEOUT,
    MODEL_NAME,
    OLLAMA_URL,
    READ_TIMEOUT,
)


class OllamaTransport:
    """
    Low-level HTTP transport
    untuk Ollama.

    Bertugas mengirim request HTTP
    dan menerima response streaming
    dari Ollama tanpa mengetahui
    business logic Runtime.
    """

    def __init__(self):

        self.model = MODEL_NAME

        self.url = OLLAMA_URL

        self.connect_timeout = CONNECT_TIMEOUT

        self.read_timeout = READ_TIMEOUT

    def generate(
        self,
        prompt: str,
    ) -> dict:

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
        }

        response = requests.post(
            self.url,
            json=payload,
            timeout=(
                self.connect_timeout,
                self.read_timeout,
            ),
            stream=True,
        )

        response.raise_for_status()

        parts = []

        last_chunk = {}

        for line in response.iter_lines():

            if not line:
                continue

            item = json.loads(
                line.decode("utf-8")
            )

            last_chunk = item

            if "response" in item:

                parts.append(
                    item["response"]
                )

            if item.get(
                "done",
                False,
            ):
                break

        return {

            "provider": "ollama",

            "model": last_chunk.get(
                "model",
                self.model,
            ),

            "response": "".join(
                parts
            ),

            "done": last_chunk.get(
                "done",
                True,
            ),

            "done_reason": last_chunk.get(
                "done_reason"
            ),

            "raw": last_chunk,
        }

    def generate_stream(
        self,
        prompt: str,
    ):

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
        }

        response = requests.post(
            self.url,
            json=payload,
            timeout=(
                self.connect_timeout,
                self.read_timeout,
            ),
            stream=True,
        )

        response.raise_for_status()

        for line in response.iter_lines():

            if not line:
                continue

            chunk = json.loads(
                line.decode("utf-8")
            )

            text = chunk.get(
                "response",
                "",
            )

            if text:

                yield text

            if chunk.get(
                "done",
                False,
            ):
                break
