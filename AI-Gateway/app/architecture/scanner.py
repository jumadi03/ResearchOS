"""
ResearchOS Architecture Scanner.

Discovers architecture artifacts
from the project filesystem.
"""

from dataclasses import dataclass
from pathlib import Path

from .models import ArchitectureArtifact


@dataclass(
    frozen=True,
    slots=True,
)
class ArchitectureScanner:
    """
    Foundation Architecture Scanner.

    Performs filesystem discovery.
    """

    root: Path

    #
    # Directories ignored by the
    # Architecture Discovery Layer.
    #
    IGNORED_DIRECTORIES = (
        ".venv",
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        "logs",
    )

    def is_project_file(
        self,
        path: Path,
    ) -> bool:
        """
        Determine whether the file belongs
        to the ResearchOS project.
        """

        return not any(
            ignored in path.parts
            for ignored in self.IGNORED_DIRECTORIES
        )

    def discover_python_files(
        self,
    ) -> tuple[Path, ...]:
        """
        Discover every project Python file.
        """

        return tuple(
            sorted(
                path
                for path in self.root.rglob("*.py")
                if self.is_project_file(path)
            )
        )

    def load_source(
        self,
        path: Path,
    ) -> str:
        """
        Load source code.

        Foundation implementation.
        """

        return path.read_text(
            encoding="utf-8",
        )

    def build_artifact(
        self,
        path: Path,
    ) -> ArchitectureArtifact:
        """
        Build one ArchitectureArtifact.
        """

        module = (
            str(path.with_suffix(""))
            .replace("\\", ".")
            .replace("/", ".")
        )

        source = self.load_source(
            path,
        )

        return ArchitectureArtifact(
            artifact_id=module,
            name=path.stem,
            artifact_type="PythonModule",
            module=module,
            source=source,
            metadata={
                "path": str(path),
                "size": path.stat().st_size,
                "encoding": "utf-8",
            },
        )

    def scan(
        self,
    ) -> tuple[
        ArchitectureArtifact,
        ...
    ]:
        """
        Scan the project.
        """

        python_files = (
            self.discover_python_files()
        )

        artifacts = tuple(
            self.build_artifact(path)
            for path in python_files
        )

        print()

        print(
            f"Scanning project: {self.root}"
        )

        print(
            "Applying project filters..."
        )

        print(
            f"Discovered {len(python_files)} project Python file(s)."
        )

        print(
            f"Built {len(artifacts)} architecture artifact(s)."
        )

        return artifacts