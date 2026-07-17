from pathlib import Path
import ast


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


def test_monitoring_executor_depends_on_ports_not_postgres_adapter() -> None:
    repository = Path(__file__).resolve().parents[4]
    executor = (
        repository
        / "AI-Gateway"
        / "app"
        / "knowledge"
        / "monitoring"
        / "executor.py"
    )
    tree = ast.parse(executor.read_text(encoding="utf-8"))
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }

    assert "app.knowledge.repositories.postgres" not in imports


def test_ci_executes_continuous_monitoring_storage_verifier() -> None:
    repository = Path(__file__).resolve().parents[4]
    workflow = (
        repository / ".github" / "workflows" / "architecture-quality-gates.yml"
    ).read_text(encoding="utf-8")

    assert "verify/continuous_monitoring.py" in workflow
    assert "continuous-monitoring=passed" in (
        repository / "deploy" / "verify" / "continuous_monitoring.py"
    ).read_text(encoding="utf-8")
