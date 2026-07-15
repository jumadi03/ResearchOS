"""Metrics, correlation middleware, readiness, and durable audit events."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from threading import RLock
from time import perf_counter
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, Response, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware

from app.architecture.authentication import ArchitectureRole
from app.architecture.persistence import InterProcessFileLock
from app.logger import correlation_id_context, logger


class MetricsRegistry:
    """Small thread-safe Prometheus-compatible metrics registry."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)
        self._durations: dict[
            tuple[str, tuple[tuple[str, str], ...]], tuple[int, float]
        ] = {}

    @staticmethod
    def _key(name: str, labels: dict[str, str] | None) -> tuple[str, tuple[tuple[str, str], ...]]:
        return name, tuple(sorted((labels or {}).items()))

    def increment(
        self, name: str, value: float = 1, *, labels: dict[str, str] | None = None
    ) -> None:
        with self._lock:
            self._counters[self._key(name, labels)] += value

    def observe(
        self, name: str, value: float, *, labels: dict[str, str] | None = None
    ) -> None:
        key = self._key(name, labels)
        with self._lock:
            count, total = self._durations.get(key, (0, 0.0))
            self._durations[key] = count + 1, total + value

    @staticmethod
    def _labels(labels: tuple[tuple[str, str], ...]) -> str:
        if not labels:
            return ""
        rendered = ",".join(
            f'{name}="{value.replace(chr(34), chr(92) + chr(34))}"'
            for name, value in labels
        )
        return "{" + rendered + "}"

    def prometheus_text(self) -> str:
        with self._lock:
            lines = [
                f"{name}{self._labels(labels)} {value:g}"
                for (name, labels), value in sorted(self._counters.items())
            ]
            for (name, labels), (count, total) in sorted(self._durations.items()):
                rendered = self._labels(labels)
                lines.append(f"{name}_count{rendered} {count}")
                lines.append(f"{name}_sum{rendered} {total:.9f}")
        return "\n".join(lines) + "\n"


@dataclass(frozen=True, slots=True)
class AuditTrail:
    path: Path

    def record(
        self,
        event_type: str,
        *,
        actor: str | None,
        outcome: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        occurred_at = datetime.now(timezone.utc).isoformat()
        correlation_id = correlation_id_context.get()
        seed = f"{event_type}:{actor}:{outcome}:{occurred_at}:{correlation_id}"
        event = {
            "event_id": f"audit:{sha256(seed.encode()).hexdigest()[:16]}",
            "event_type": event_type,
            "actor": actor,
            "outcome": outcome,
            "occurred_at": occurred_at,
            "correlation_id": correlation_id,
            "details": details or {},
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        encoded = (json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n").encode(
            "utf-8"
        )
        with InterProcessFileLock(self.path.with_suffix(".lock")):
            with self.path.open("ab") as handle:
                handle.write(encoded)
                handle.flush()
                import os

                os.fsync(handle.fileno())
        return event


class CorrelationMiddleware(BaseHTTPMiddleware):
    _valid = re.compile(r"^[A-Za-z0-9._-]{1,128}$")

    def __init__(self, app, metrics: MetricsRegistry) -> None:
        super().__init__(app)
        self.metrics = metrics

    async def dispatch(self, request: Request, call_next):
        supplied = request.headers.get("X-Correlation-ID")
        correlation_id = supplied if supplied and self._valid.fullmatch(supplied) else uuid4().hex
        token = correlation_id_context.set(correlation_id)
        started = perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Correlation-ID"] = correlation_id
            return response
        finally:
            duration = perf_counter() - started
            route = request.scope.get("route")
            metric_path = getattr(route, "path", request.url.path)
            labels = {
                "method": request.method,
                "path": metric_path,
                "status": str(status),
            }
            self.metrics.increment("researchos_http_requests_total", labels=labels)
            self.metrics.observe("researchos_http_request_duration_seconds", duration, labels=labels)
            logger.info(
                "http_request",
                extra={
                    "event": "http_request",
                    "fields": {**labels, "duration_seconds": round(duration, 9)},
                },
            )
            correlation_id_context.reset(token)


router = APIRouter(tags=["operations"])
bearer = HTTPBearer(auto_error=False)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready(request: Request, response: Response) -> dict[str, Any]:
    service = request.app.state.architecture_service
    try:
        with InterProcessFileLock(
            service.store.root / ".pipeline.lock", timeout=0.1
        ):
            persistence_lock = True
    except (OSError, TimeoutError):
        persistence_lock = False
    checks = {
        "project_root": service.project_root.exists(),
        "output_root": service.store.root.exists(),
        "persistence_lock": persistence_lock,
        "authentication_configured": bool(
            request.app.state.architecture_authenticator.principals_by_token
        ),
    }
    is_ready = all(checks.values())
    response.status_code = 200 if is_ready else 503
    return {"status": "ready" if is_ready else "not_ready", "checks": checks}


@router.get("/metrics")
def metrics(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
) -> Response:
    authorization = (
        f"{credentials.scheme} {credentials.credentials}" if credentials else None
    )
    try:
        principal = request.app.state.architecture_authenticator.authenticate(
            authorization
        )
    except PermissionError as exc:
        request.app.state.audit_trail.record(
            "metrics_authentication",
            actor=None,
            outcome="denied",
            details={"reason": str(exc)},
        )
        raise HTTPException(401, str(exc), headers={"WWW-Authenticate": "Bearer"}) from exc
    if not principal.has_role(ArchitectureRole.AUDITOR):
        request.app.state.audit_trail.record(
            "metrics_authorization",
            actor=principal.actor_id,
            outcome="denied",
            details={"required_role": "auditor"},
        )
        raise HTTPException(403, "Role required: auditor")
    return Response(
        request.app.state.metrics_registry.prometheus_text(),
        media_type="text/plain; version=0.0.4",
    )
