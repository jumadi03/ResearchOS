"""Prometheus metrics endpoint owned by the background worker process."""

from __future__ import annotations

from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import RLock, Thread
from time import time


def _label(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


class WorkerMetrics:
    def __init__(self) -> None:
        self._lock = RLock()
        self._jobs: dict[tuple[str, str], int] = defaultdict(int)
        self._durations: dict[tuple[str, str], tuple[int, float]] = {}
        self._queue: dict[str, int] = {}
        self._heartbeat_unixtime = 0.0

    def heartbeat(self) -> None:
        with self._lock:
            self._heartbeat_unixtime = time()

    def observe_job(self, job_type: str, outcome: str, duration: float) -> None:
        key = (job_type, outcome)
        with self._lock:
            self._jobs[key] += 1
            count, total = self._durations.get(key, (0, 0.0))
            self._durations[key] = (count + 1, total + duration)

    def set_queue(self, counts: dict[str, int]) -> None:
        with self._lock:
            self._queue = dict(counts)

    def render(self) -> str:
        with self._lock:
            lines = [
                "# HELP researchos_worker_up Worker metrics process is running.",
                "# TYPE researchos_worker_up gauge",
                "researchos_worker_up 1",
                "# HELP researchos_worker_heartbeat_unixtime Last successful database heartbeat.",
                "# TYPE researchos_worker_heartbeat_unixtime gauge",
                f"researchos_worker_heartbeat_unixtime {self._heartbeat_unixtime:.3f}",
                "# HELP researchos_worker_jobs_total Jobs handled by type and outcome.",
                "# TYPE researchos_worker_jobs_total counter",
            ]
            for (job_type, outcome), value in sorted(self._jobs.items()):
                labels = (
                    f'job_type="{_label(job_type)}",outcome="{_label(outcome)}"'
                )
                lines.append(f"researchos_worker_jobs_total{{{labels}}} {value}")
                count, total = self._durations[(job_type, outcome)]
                lines.append(
                    f"researchos_worker_job_duration_seconds_count{{{labels}}} {count}"
                )
                lines.append(
                    f"researchos_worker_job_duration_seconds_sum{{{labels}}} {total:.9f}"
                )
            lines.extend((
                "# HELP researchos_worker_queue_jobs Jobs currently recorded by status.",
                "# TYPE researchos_worker_queue_jobs gauge",
            ))
            for status in ("pending", "running", "complete", "failed", "dead_letter"):
                lines.append(
                    f'researchos_worker_queue_jobs{{status="{status}"}} '
                    f'{self._queue.get(status, 0)}'
                )
        return "\n".join(lines) + "\n"

    def serve(self, port: int) -> ThreadingHTTPServer:
        metrics = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path != "/metrics":
                    self.send_error(404)
                    return
                body = metrics.render().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; version=0.0.4")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, _format, *_args):
                return

        server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
        Thread(target=server.serve_forever, name="worker-metrics", daemon=True).start()
        return server
