from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import uuid


@dataclass
class RuntimeMetrics:
    request_id: str
    provider: str
    model: str
    status: str
    duration_ms: float
    timestamp: datetime
    success: bool
    error_type: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None


class MetricsCollector:

    def __init__(self):
        self._metrics: list[RuntimeMetrics] = []

    def collect(self, canonical_response: dict) -> None:

        metrics = RuntimeMetrics(
            request_id=str(uuid.uuid4()),
            provider=canonical_response.get("provider", ""),
            model=canonical_response.get("model", ""),
            status="success",
            duration_ms=0.0,          # Placeholder Sprint-001H
            timestamp=datetime.now(),
            success=True,
        )

        self._metrics.append(metrics)

        print("========== METRICS ==========")
        print(metrics)
        print("=============================")

    def export(self) -> list[RuntimeMetrics]:
        return self._metrics.copy()