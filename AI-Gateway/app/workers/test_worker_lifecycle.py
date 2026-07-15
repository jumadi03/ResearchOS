from types import SimpleNamespace

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


class _Queue:
    def __init__(self, result=None):
        self.result = result

    def empty(self):
        return self.result is None

    def get(self, timeout=None):
        assert timeout == 1
        if self.result is None:
            from queue import Empty
            raise Empty
        return self.result


class _Process:
    exitcode = 0

    def __init__(self, alive=False):
        self.alive = alive
        self.terminated = False

    def start(self):
        return None

    def join(self, _timeout=None):
        return None

    def is_alive(self):
        return self.alive and not self.terminated

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.terminated = True


class _Context:
    def __init__(self, process, result=None):
        self.process = process
        self.queue = _Queue(result)

    def Queue(self, maxsize):
        assert maxsize == 1
        return self.queue

    def Process(self, **_kwargs):
        return self.process


def test_job_timeout_terminates_isolated_process(monkeypatch):
    process = _Process(alive=True)
    monkeypatch.setattr(
        worker.multiprocessing, "get_context",
        lambda _method: _Context(process),
    )
    try:
        worker.execute_with_timeout("postgresql://test", "parse_document", {})
    except TimeoutError:
        pass
    else:
        raise AssertionError("Timed-out job must raise TimeoutError")
    assert process.terminated is True


def test_isolated_job_failure_is_propagated(monkeypatch):
    monkeypatch.setattr(
        worker.multiprocessing, "get_context",
        lambda _method: _Context(_Process(), ("failed", "parser failed")),
    )
    try:
        worker.execute_with_timeout("postgresql://test", "parse_document", {})
    except RuntimeError as exc:
        assert str(exc) == "parser failed"
    else:
        raise AssertionError("Child failure must be propagated")
def test_worker_records_heartbeat_and_removes_stale_workers(monkeypatch):
    statements = []

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def execute(self, statement, parameters=None):
            statements.append((statement, parameters))

        def fetchall(self):
            return []

    class Transaction:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    connection = SimpleNamespace(
        transaction=lambda: Transaction(), cursor=lambda: Cursor()
    )

    worker.record_heartbeat(connection)

    assert "INSERT INTO worker_heartbeats" in statements[0][0]
    assert statements[0][1] == (worker.WORKER_ID,)
    assert "DELETE FROM worker_heartbeats" in statements[1][0]
    assert "FROM background_jobs GROUP BY status" in statements[2][0]
