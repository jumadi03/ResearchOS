from pathlib import Path

import pytest

from app.architecture.persistence import InterProcessFileLock, atomic_write
from app.architecture.pipeline_service import ArchitecturePipelineService


def test_atomic_write_replaces_complete_file_without_temp_residue(
    tmp_path: Path,
) -> None:
    target = tmp_path / "state" / "snapshot.json"
    atomic_write(target, '{"version":1}')
    atomic_write(target, '{"version":2}')
    assert target.read_text(encoding="utf-8") == '{"version":2}'
    assert tuple(target.parent.glob(".tmp-*")) == ()


def test_interprocess_lock_times_out_when_already_held(tmp_path: Path) -> None:
    lock_path = tmp_path / ".pipeline.lock"
    with InterProcessFileLock(lock_path):
        with pytest.raises(TimeoutError):
            with InterProcessFileLock(lock_path, timeout=0.1):
                pass


def test_service_startup_removes_only_internal_temporary_entries(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    output = tmp_path / "output"
    interrupted_file = output / "runs" / "run_x" / ".tmp-review.json-dead"
    interrupted_file.parent.mkdir(parents=True)
    interrupted_file.write_text("partial", encoding="utf-8")
    interrupted_directory = output / "runs" / "run_x" / "arc" / ".tmp-arc-dead"
    interrupted_directory.mkdir(parents=True)
    (interrupted_directory / "partial").write_text("partial", encoding="utf-8")
    unrelated = output / "runs" / "run_x" / "keep.txt"
    unrelated.write_text("keep", encoding="utf-8")

    service = ArchitecturePipelineService(project, output)

    assert not interrupted_file.exists()
    assert not interrupted_directory.exists()
    assert unrelated.read_text(encoding="utf-8") == "keep"
    assert len(service.recovered_temporary_entries) == 2
