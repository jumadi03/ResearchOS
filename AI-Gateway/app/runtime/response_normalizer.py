from app.runtime.metrics import record


class ResponseNormalizer:
    """
    Mengubah Runtime Response menjadi
    Canonical Response ResearchOS.

    Pada tahap ini seluruh adapter sudah
    mengembalikan Runtime Response sehingga
    normalizer tidak lagi berhubungan dengan
    format asli provider.
    """

    def normalize(self, provider_name: str, response: dict):

        canonical = {
            "provider": response["provider"],
            "model": response["model"],
            "text": response["text"],
            "raw": response,
        }

        record(canonical)

        return canonical