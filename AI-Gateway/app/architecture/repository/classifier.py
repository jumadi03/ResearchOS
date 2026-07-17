"""Deterministic primary file classification for FMA-001."""

from pathlib import PurePosixPath

from .models import RepositoryFileClassification


class RepositoryClassifier:
    """Classify a repository-relative path without inferring compliance."""

    TEMPORARY_PARTS = frozenset({
        ".git", ".mypy_cache", ".pytest_cache", ".tmp", ".venv",
        "__pycache__", "cache", "logs", "workspace",
    })
    GENERATED_PARTS = frozenset({
        "build", "coverage", "dist", "generated",
    })
    DOCUMENT_EXTENSIONS = frozenset({".md", ".rst", ".txt"})
    CONFIGURATION_EXTENSIONS = frozenset({
        ".cff", ".env", ".example", ".ini", ".json", ".toml", ".yaml", ".yml",
    })
    SCRIPT_EXTENSIONS = frozenset({".bat", ".ps1", ".sh", ".sql"})
    DATASET_EXTENSIONS = frozenset({
        ".csv", ".jsonl", ".ndjson", ".parquet", ".tsv",
    })
    ARTIFACT_EXTENSIONS = frozenset({
        ".gz", ".pdf", ".png", ".tar", ".whl", ".zip",
    })
    CODE_EXTENSIONS = frozenset({
        ".css", ".html", ".js", ".py", ".pyi", ".ts", ".tsx",
    })

    def classify(
        self, path: str,
    ) -> tuple[RepositoryFileClassification, str]:
        item = PurePosixPath(path)
        parts = tuple(part.lower() for part in item.parts)
        suffix = item.suffix.lower()
        name = item.name.lower()

        if any(part in self.TEMPORARY_PARTS for part in parts) or suffix in {
            ".log", ".pyc", ".temp", ".tmp",
        }:
            return (
                RepositoryFileClassification.TEMPORARY,
                "temporary path or runtime extension",
            )
        if any(part in self.GENERATED_PARTS for part in parts):
            return (
                RepositoryFileClassification.GENERATED,
                "generated-output directory",
            )
        if (
            "tests" in parts
            or name.startswith("test_")
            or name.endswith("_test.py")
        ):
            return RepositoryFileClassification.TEST, "test path or naming convention"
        if suffix in self.DATASET_EXTENSIONS:
            return RepositoryFileClassification.DATASET, "dataset extension"
        if suffix in self.ARTIFACT_EXTENSIONS:
            return RepositoryFileClassification.ARTIFACT, "artifact extension"
        if (
            parts[0:1] == ("scripts",)
            or suffix in self.SCRIPT_EXTENSIONS
        ):
            return RepositoryFileClassification.SCRIPT, "script path or extension"
        if (
            suffix in self.DOCUMENT_EXTENSIONS
            or name in {"license", "notice"}
        ):
            return RepositoryFileClassification.DOCUMENT, "document extension or name"
        if (
            parts[0:1] == (".github",)
            or suffix in self.CONFIGURATION_EXTENSIONS
            or name in {
                ".dockerignore", ".gitignore", "dockerfile",
            }
            or name.startswith("dockerfile.")
        ):
            return (
                RepositoryFileClassification.CONFIGURATION,
                "configuration path, extension, or name",
            )
        if suffix in self.CODE_EXTENSIONS:
            return RepositoryFileClassification.CODE, "source-code extension"
        return (
            RepositoryFileClassification.UNKNOWN,
            "no FMA-001 classification rule matched",
        )
