from app.workers import main as worker


def test_retry_delay_is_exponential_and_bounded(monkeypatch):
    monkeypatch.setattr(worker, "JOB_RETRY_BASE_SECONDS", 5)
    assert worker.retry_delay(1) == 5
    assert worker.retry_delay(2) == 10
    assert worker.retry_delay(20) == 3600


def test_failure_disposition_retries_then_dead_letters(monkeypatch):
    monkeypatch.setattr(worker, "JOB_MAX_ATTEMPTS", 3)
    monkeypatch.setattr(worker, "JOB_RETRY_BASE_SECONDS", 5)
    assert worker.failure_disposition(1) == ("pending", 5)
    assert worker.failure_disposition(2) == ("pending", 10)
    assert worker.failure_disposition(3) == ("dead_letter", None)


def test_stop_request_is_graceful(monkeypatch):
    monkeypatch.setattr(worker, "_stop_requested", False)
    worker.request_stop()
    assert worker._stop_requested is True
