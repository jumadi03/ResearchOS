"""
ResearchOS Architecture Scanner.

Discovers architecture artifacts
from the project filesystem.
"""

from dataclasses import dataclass
from pathlib import Path
from pathlib import PurePosixPath

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
        "build",
        "tmp",
        ".tmp",
    )

    def is_project_file(
        self,
        path: Path,
    ) -> bool:
        """
        Determine whether the file belongs
        to the ResearchOS project.
        """

        try:
            relative = path.resolve().relative_to(self.root.resolve())
        except ValueError:
            return False
        return not any(
            ignored in relative.parts
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

        try:
            relative_path = path.relative_to(self.root)
        except ValueError:
            relative_path = path

        module = (
            str(relative_path.with_suffix(""))
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
                "path": relative_path.as_posix(),
                "size": path.stat().st_size,
                "encoding": "utf-8",
            },
        )

    def scan(
        self,
        source_paths: tuple[str, ...] | None = None,
    ) -> tuple[
        ArchitectureArtifact,
        ...
    ]:
        """
        Scan the project.
        """

        if source_paths is None:
            python_files = self.discover_python_files()
        else:
            if len(source_paths) != len(set(source_paths)):
                raise ValueError("Duplicate architecture source paths are not allowed")
            selected = []
            root = self.root.resolve(strict=True)
            for value in source_paths:
                normalized = value.replace("\\", "/")
                item = PurePosixPath(normalized)
                if (
                    not normalized
                    or item.is_absolute()
                    or any(part in {"", ".", ".."} for part in item.parts)
                    or item.suffix.lower() != ".py"
                ):
                    raise ValueError(
                        f"Unsafe architecture source path: {value}"
                    )
                target = self.root.joinpath(*item.parts)
                unresolved = self.root
                for part in item.parts:
                    unresolved = unresolved / part
                    if unresolved.is_symlink():
                        raise ValueError(
                            f"Symbolic links are not architecture sources: {value}"
                        )
                resolved = target.resolve(strict=True)
                try:
                    resolved.relative_to(root)
                except ValueError as exc:
                    raise ValueError(
                        f"Architecture source escapes scan root: {value}"
                    ) from exc
                if not resolved.is_file():
                    raise ValueError(
                        f"Architecture source is not a file: {value}"
                    )
                selected.append(target)
            python_files = tuple(sorted(selected))

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
