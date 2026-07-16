from pathlib import Path


def test_container_build_retry_is_bounded_and_fail_closed() -> None:
    repository = Path(__file__).resolve().parents[4]
    workflow = (
        repository / ".github" / "workflows" / "architecture-quality-gates.yml"
    ).read_text(encoding="utf-8")

    assert "docker version" in workflow
    assert workflow.count("for attempt in 1 2 3") == 2
    assert "API image build failed after 3 attempts" in workflow
    assert "Backup image build failed after 3 attempts" in workflow
    assert workflow.count('exit 1') >= 2
