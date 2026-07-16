"""Policy-enforced document acquisition."""

from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from ipaddress import ip_address
from typing import Callable
from urllib.parse import urljoin, urlparse

import requests

from app.knowledge.ingestion.models import (
    AccessStatus, AcquisitionResult, AcquisitionStatus, DocumentCandidate,
)
from app.knowledge.models import SourceRecord


def bind_candidate_to_source(
    candidate: DocumentCandidate, source: SourceRecord,
) -> DocumentCandidate:
    urls, access_status, license_value = source_acquisition_policy(source)
    if candidate.url is not None and candidate.url not in urls:
        raise ValueError(
            "Document URL does not match enumerated source metadata"
        )
    if candidate.access_status is not access_status:
        raise ValueError(
            "Document access status does not match enumerated source metadata"
        )
    if (candidate.license or "").strip().casefold() != (
        license_value or ""
    ).strip().casefold():
        raise ValueError(
            "Document license does not match enumerated source metadata"
        )
    return replace(
        candidate,
        url=candidate.url if candidate.url in urls else None,
        access_status=access_status,
        license=license_value,
        source_definition_id=source.source_definition_id,
        query_family_id=source.query_family_id,
    )


def source_acquisition_policy(
    source: SourceRecord,
) -> tuple[tuple[str, ...], AccessStatus, str | None]:
    raw = source.raw
    candidates = []

    def add(value) -> None:
        if isinstance(value, str) and value.strip():
            candidates.append(value.strip())

    open_access = raw.get("open_access") or {}
    best_location = raw.get("best_oa_location") or {}
    primary_location = raw.get("primary_location") or {}
    open_pdf = raw.get("openAccessPdf") or {}
    add(open_access.get("oa_url"))
    add(best_location.get("pdf_url"))
    add(primary_location.get("pdf_url"))
    add(open_pdf.get("url"))
    for link in raw.get("link") or ():
        if str(link.get("content-type") or "").casefold() == "application/pdf":
            add(link.get("URL") or link.get("url"))
    urls = tuple(dict.fromkeys(
        item for item in candidates if DocumentAcquirer._safe_https_url(item)
    ))

    license_value = _source_license(raw, best_location, primary_location)
    explicitly_open = bool(
        open_access.get("is_oa") is True
        or open_pdf
        or any(
            str(link.get("content-type") or "").casefold()
            == "application/pdf"
            for link in raw.get("link") or ()
        )
    )
    status = (
        AccessStatus.OPEN
        if explicitly_open and urls and license_value
        else AccessStatus.UNKNOWN
    )
    return urls, status, license_value


def _source_license(raw: dict, *locations: dict) -> str | None:
    values = (raw.get("license"), *(item.get("license") for item in locations))
    for value in values:
        items = value if isinstance(value, list) else (value,)
        for item in items:
            if isinstance(item, str) and item.strip():
                return item.strip()
            if isinstance(item, dict):
                candidate = item.get("URL") or item.get("url")
                if isinstance(candidate, str) and candidate.strip():
                    return candidate.strip()
    return None


class DocumentAcquirer:
    _CAPTURE_HEADERS = frozenset({
        "accept-ranges", "cache-control", "content-disposition",
        "content-encoding", "content-language", "content-length",
        "content-type", "date", "etag", "expires", "last-modified", "vary",
    })
    def __init__(
        self, *, transport: Callable = requests.get,
        timeout: float = 30.0, max_bytes: int = 25_000_000,
        max_redirects: int = 5,
    ) -> None:
        self.transport = transport
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.max_redirects = max_redirects

    def acquire(self, candidate: DocumentCandidate, *, acquired_at: str) -> AcquisitionResult:
        reason = self._policy_reason(candidate)
        if reason:
            return self._result(candidate, acquired_at, AcquisitionStatus.METADATA_ONLY, reason=reason)
        try:
            current_url = candidate.url
            redirect_chain = []
            for _ in range(self.max_redirects + 1):
                response = self.transport(
                    current_url, timeout=self.timeout, allow_redirects=False,
                )
                status_code = getattr(response, "status_code", None)
                location = response.headers.get("Location")
                if status_code not in {301, 302, 303, 307, 308} or not location:
                    break
                redirect_chain.append(current_url)
                next_url = urljoin(current_url, location)
                if not self._safe_https_url(next_url):
                    return self._result(
                        candidate, acquired_at, AcquisitionStatus.FAILED,
                        reason="Redirect or final URL is not a safe HTTPS URL",
                        final_url=next_url, http_status=status_code,
                        redirect_chain=tuple(redirect_chain),
                    )
                current_url = next_url
            else:
                return self._result(
                    candidate, acquired_at, AcquisitionStatus.FAILED,
                    reason="Redirect limit exceeded", final_url=current_url,
                    http_status=getattr(response, "status_code", None),
                    redirect_chain=tuple(redirect_chain),
                )
            response.raise_for_status()
            final_url = getattr(response, "url", None) or current_url
            if not self._safe_https_url(final_url):
                return self._result(
                    candidate, acquired_at, AcquisitionStatus.FAILED,
                    reason="Redirect or final URL is not a safe HTTPS URL",
                    final_url=final_url, http_status=getattr(
                        response, "status_code", None
                    ), redirect_chain=tuple(redirect_chain),
                )
            declared_length = self._declared_length(response)
            if declared_length is not None and declared_length > self.max_bytes:
                return self._result(
                    candidate, acquired_at, AcquisitionStatus.FAILED,
                    reason="Declared content length exceeds size limit",
                    final_url=final_url, http_status=getattr(
                        response, "status_code", None
                    ), redirect_chain=tuple(redirect_chain),
                    declared_content_length=declared_length,
                )
            media_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
            content = response.content
            if media_type != "application/pdf" or not content.startswith(b"%PDF-"):
                return self._result(
                    candidate, acquired_at, AcquisitionStatus.FAILED,
                    reason="Content is not a valid PDF", media_type=media_type,
                    final_url=final_url, http_status=getattr(
                        response, "status_code", None
                    ), redirect_chain=tuple(redirect_chain),
                    declared_content_length=declared_length,
                )
            if len(content) > self.max_bytes:
                return self._result(
                    candidate, acquired_at, AcquisitionStatus.FAILED,
                    reason="Document exceeds size limit", media_type=media_type,
                    final_url=final_url, http_status=getattr(
                        response, "status_code", None
                    ), redirect_chain=tuple(redirect_chain),
                    declared_content_length=declared_length,
                )
            return self._result(
                candidate, acquired_at, AcquisitionStatus.ACQUIRED,
                media_type=media_type, content=content, final_url=final_url,
                http_status=getattr(response, "status_code", 200),
                redirect_chain=tuple(redirect_chain),
                declared_content_length=declared_length,
                response_headers=self._capture_headers(response),
                content_encoding=self._content_encoding(response, media_type),
            )
        except requests.RequestException as exc:
            return self._result(candidate, acquired_at, AcquisitionStatus.FAILED, reason=str(exc))

    @staticmethod
    def _policy_reason(candidate: DocumentCandidate) -> str | None:
        if candidate.access_status is not AccessStatus.OPEN:
            return "Access status is not explicitly open"
        if not candidate.license or not candidate.license.strip():
            return "License is not declared"
        if not candidate.url or not DocumentAcquirer._safe_https_url(candidate.url):
            return "A valid HTTPS document URL is required"
        if not candidate.source_definition_id or not candidate.query_family_id:
            return "Canonical source and query provenance are required"
        if candidate.retrieval_method != "https_pdf":
            return "Unsupported retrieval method"
        return None

    @staticmethod
    def _result(
        candidate, acquired_at, status, *, reason=None, media_type=None,
        content=None, final_url=None, http_status=None, redirect_chain=(),
        declared_content_length=None, response_headers=(),
        content_encoding=None,
    ):
        return AcquisitionResult(
            candidate.record_id, status, acquired_at, candidate.url,
            candidate.source_provider, candidate.source_response_hash,
            candidate.license, media_type,
            sha256(content).hexdigest() if content else None,
            len(content) if content else None, reason, content,
            final_url, http_status, redirect_chain, declared_content_length,
            candidate.retrieval_method, candidate.source_definition_id,
            candidate.query_family_id,
            response_headers, content_encoding,
        )

    @staticmethod
    def _declared_length(response) -> int | None:
        raw = response.headers.get("Content-Length")
        if raw is None or raw == "":
            return None
        try:
            value = int(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError("Content-Length is invalid") from exc
        if value < 0:
            raise ValueError("Content-Length is invalid")
        return value

    @staticmethod
    def _safe_https_url(value: str) -> bool:
        parsed = urlparse(value)
        host = (parsed.hostname or "").casefold()
        if (
            parsed.scheme != "https"
            or not host
            or parsed.username is not None
            or parsed.password is not None
            or host == "localhost"
            or host.endswith(".local")
        ):
            return False
        try:
            address = ip_address(host)
        except ValueError:
            return True
        return not (
            address.is_private or address.is_loopback or address.is_link_local
            or address.is_multicast or address.is_reserved
        )

    @classmethod
    def _capture_headers(cls, response) -> tuple[tuple[str, str], ...]:
        return tuple(sorted(
            (str(key).casefold(), str(value))
            for key, value in response.headers.items()
            if str(key).casefold() in cls._CAPTURE_HEADERS
        ))

    @staticmethod
    def _content_encoding(response, media_type: str) -> str:
        explicit = getattr(response, "encoding", None)
        if explicit:
            return str(explicit)
        content_type = response.headers.get("Content-Type", "")
        for part in content_type.split(";")[1:]:
            key, _, value = part.partition("=")
            if key.strip().casefold() == "charset" and value.strip():
                return value.strip().strip("\"'")
        return "binary" if media_type == "application/pdf" else "unknown"
