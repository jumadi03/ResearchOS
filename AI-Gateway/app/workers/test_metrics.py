from urllib.error import HTTPError
from urllib.request import urlopen

from app.workers.metrics import WorkerMetrics


def test_worker_metrics_expose_lifecycle_duration_queue_and_heartbeat(monkeypatch):
    monkeypatch.setattr("app.workers.metrics.time", lambda: 1234.5)
    metrics = WorkerMetrics()
    metrics.heartbeat()
    metrics.observe_job("parse_document", "complete", 1.25)
    metrics.observe_job("parse_document", "complete", 0.75)
    metrics.set_queue({"pending": 3, "dead_letter": 1})

    rendered = metrics.render()

    assert "researchos_worker_up 1" in rendered
    assert "researchos_worker_heartbeat_unixtime 1234.500" in rendered
    assert 'job_type="parse_document",outcome="complete"} 2' in rendered
    assert 'job_type="parse_document",outcome="complete"} 2.000000000' in rendered
    assert 'researchos_worker_queue_jobs{status="pending"} 3' in rendered
    assert 'researchos_worker_queue_jobs{status="dead_letter"} 1' in rendered


def test_worker_metrics_http_endpoint_is_internal_and_prometheus_compatible():
    metrics = WorkerMetrics()
    server = metrics.serve(0)
    try:
        port = server.server_address[1]
        with urlopen(f"http://127.0.0.1:{port}/metrics") as response:
            assert response.status == 200
            assert response.headers["content-type"] == "text/plain; version=0.0.4"
            assert b"researchos_worker_up 1" in response.read()
        try:
            urlopen(f"http://127.0.0.1:{port}/not-found")
        except HTTPError as exc:
            assert exc.code == 404
        else:
            raise AssertionError("Unknown metrics paths must return 404")
    finally:
        server.shutdown()
        server.server_close()


def test_worker_metric_labels_are_escaped():
    metrics = WorkerMetrics()
    metrics.observe_job('bad"type\n', "failed", 0.1)

    rendered = metrics.render()

    assert 'job_type="bad\\"type\\n"' in rendered
