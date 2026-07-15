"""Policy-enforced document acquisition."""

from __future__ import annotations

from hashlib import sha256
from typing import Callable
from urllib.parse import urlparse

import requests

from app.knowledge.ingestion.models import (
    AccessStatus, AcquisitionResult, AcquisitionStatus, DocumentCandidate,
)


class DocumentAcquirer:
    def __init__(
        self, *, transport: Callable = requests.get,
        timeout: float = 30.0, max_bytes: int = 25_000_000,
    ) -> None:
        self.transport = transport
        self.timeout = timeout
        self.max_bytes = max_bytes

    def acquire(self, candidate: DocumentCandidate, *, acquired_at: str) -> AcquisitionResult:
        reason = self._policy_reason(candidate)
        if reason:
            return self._result(candidate, acquired_at, AcquisitionStatus.METADATA_ONLY, reason=reason)
        try:
            response = self.transport(candidate.url, timeout=self.timeout, allow_redirects=True)
            response.raise_for_status()
            media_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
            content = response.content
            if media_type != "application/pdf" or not content.startswith(b"%PDF-"):
                return self._result(candidate, acquired_at, AcquisitionStatus.FAILED, reason="Content is not a valid PDF", media_type=media_type)
            if len(content) > self.max_bytes:
                return self._result(candidate, acquired_at, AcquisitionStatus.FAILED, reason="Document exceeds size limit", media_type=media_type)
            return self._result(candidate, acquired_at, AcquisitionStatus.ACQUIRED, media_type=media_type, content=content)
        except requests.RequestException as exc:
            return self._result(candidate, acquired_at, AcquisitionStatus.FAILED, reason=str(exc))

    @staticmethod
    def _policy_reason(candidate: DocumentCandidate) -> str | None:
        if candidate.access_status is not AccessStatus.OPEN:
            return "Access status is not explicitly open"
        if not candidate.license or not candidate.license.strip():
            return "License is not declared"
        if not candidate.url or urlparse(candidate.url).scheme != "https":
            return "A valid HTTPS document URL is required"
        return None

    @staticmethod
    def _result(candidate, acquired_at, status, *, reason=None, media_type=None, content=None):
        return AcquisitionResult(
            candidate.record_id, status, acquired_at, candidate.url,
            candidate.source_provider, candidate.source_response_hash,
            candidate.license, media_type,
            sha256(content).hexdigest() if content else None,
            len(content) if content else None, reason, content,
        )
