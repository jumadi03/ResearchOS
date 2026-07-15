"""Transactional filesystem primitives for architecture governance state."""

from __future__ import annotations

from contextlib import AbstractContextManager
import os
from pathlib import Path
import shutil
from time import monotonic, sleep
from uuid import uuid4


class InterProcessFileLock(AbstractContextManager["InterProcessFileLock"]):
    """Portable advisory exclusive lock backed by one server-controlled file."""

    def __init__(self, path: Path, *, timeout: float = 10.0) -> None:
        self.path = path
        self.timeout = timeout
        self._handle = None

    def __enter__(self) -> "InterProcessFileLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+b")
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
            os.fsync(handle.fileno())
        deadline = monotonic() + self.timeout
        while True:
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                self._handle = handle
                return self
            except OSError as exc:
                if monotonic() >= deadline:
                    handle.close()
                    raise TimeoutError(
                        f"Timed out waiting for persistence lock: {self.path}"
                    ) from exc
                sleep(0.05)

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if self._handle is None:
            return
        self._handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(self._handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        self._handle.close()
        self._handle = None


def atomic_write(path: Path, content: str | bytes) -> None:
    """Commit a complete file using fsync and same-directory atomic replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".tmp-{path.name}-{uuid4().hex}"
    data = content if isinstance(content, bytes) else content.encode("utf-8")
    try:
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def remove_internal_temporary_entries(root: Path) -> tuple[Path, ...]:
    """Remove only internal `.tmp-` entries left by interrupted commits."""
    if not root.exists():
        return ()
    entries = sorted(
        (path for path in root.rglob(".tmp-*") if path.name.startswith(".tmp-")),
        key=lambda path: len(path.parts),
        reverse=True,
    )
    removed: list[Path] = []
    for path in entries:
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
        removed.append(path)
    return tuple(removed)
