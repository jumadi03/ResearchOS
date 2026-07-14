"""
Smoke Test + Contract Test
for Architecture Scanner.
"""

from pathlib import Path

from app.architecture import (
    ArchitectureArtifact,
    ArchitectureScanner,
)


def main() -> None:
    #
    # Arrange
    #
    scanner = ArchitectureScanner(
        root=Path("."),
    )

    #
    # Act
    #
    python_files = (
        scanner.discover_python_files()
    )

    artifacts = scanner.scan()

    #
    # Smoke Test
    #
    print(
        "Scanner      :",
        scanner,
    )

    print(
        "Root         :",
        scanner.root,
    )

    print(
        "Python Files :",
        len(python_files),
    )

    print(
        "Artifacts    :",
        len(artifacts),
    )

    if python_files:
        print(
            "First File   :",
            python_files[0],
        )

        print(
            "Last File    :",
            python_files[-1],
        )

    if artifacts:
        first = artifacts[0]

        print(
            "First Module :",
            first.module,
        )

        print(
            "Source Size  :",
            len(first.source),
        )

    #
    # Contract Test
    #
    assert scanner.root == Path(".")

    assert isinstance(
        python_files,
        tuple,
    )

    assert isinstance(
        artifacts,
        tuple,
    )

    assert len(
        artifacts
    ) == len(
        python_files
    )

    #
    # Filter Contract
    #
    for path in python_files:

        assert ".venv" not in path.parts

        assert "__pycache__" not in path.parts

        assert ".git" not in path.parts

        assert ".pytest_cache" not in path.parts

        assert ".mypy_cache" not in path.parts

        assert "logs" not in path.parts

    #
    # Artifact Contract
    #
    if artifacts:

        first = artifacts[0]

        assert isinstance(
            first,
            ArchitectureArtifact,
        )

        assert isinstance(
            first.source,
            str,
        )

        assert (
            "path"
            in first.metadata
        )

        assert (
            "size"
            in first.metadata
        )

        assert (
            "encoding"
            in first.metadata
        )

    #
    # Repository Contract
    #
    assert any(
        isinstance(
            artifact.source,
            str,
        )
        for artifact in artifacts
    )

    assert any(
        len(
            artifact.source
        ) > 0
        for artifact in artifacts
    )

    print()

    print("CONTRACT TEST : PASS")

    print("PASS")


if __name__ == "__main__":
    main()