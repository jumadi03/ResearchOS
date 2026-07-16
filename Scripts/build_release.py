"""Build deterministic ResearchOS release artifacts and integrity metadata."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tomllib
import uuid
import zipfile


ROOT = Path(__file__).resolve().parents[1]
GATEWAY = ROOT / "AI-Gateway"
OUTPUT = ROOT / "dist" / "release"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_metadata() -> dict:
    with (GATEWAY / "pyproject.toml").open("rb") as stream:
        return tomllib.load(stream)["project"]


def declared_version() -> str:
    version = project_metadata()["version"]
    expected = {
        "CITATION.cff": re.search(
            r"(?m)^version:\s*([^\s]+)", (ROOT / "CITATION.cff").read_text()
        ).group(1),
        "AI-Gateway/.env.example": {
            line.split("=", 1)[0]: line.split("=", 1)[1]
            for line in (GATEWAY / ".env.example").read_text().splitlines()
            if "=" in line
        }["APP_VERSION"],
        "deploy/stack.env.example": {
            line.split("=", 1)[0]: line.split("=", 1)[1]
            for line in (ROOT / "deploy" / "stack.env.example").read_text().splitlines()
            if "=" in line
        }["APP_VERSION"],
    }
    mismatches = {name: value for name, value in expected.items() if value != version}
    if mismatches:
        raise RuntimeError(f"Release version mismatch: {mismatches}")
    return version


def source_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    files = []
    for value in result.stdout.splitlines():
        path = ROOT / value
        if path.is_file() and not path.resolve().is_relative_to((ROOT / "dist").resolve()):
            files.append(path)
    return sorted(files, key=lambda item: item.relative_to(ROOT).as_posix())


def source_archive(version: str) -> Path:
    target = OUTPUT / f"ResearchOS-{version}-source.zip"
    prefix = f"ResearchOS-{version}/"
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in source_files():
            relative = path.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo(prefix + relative, date_time=(2026, 7, 16, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if path.suffix in {".sh", ".py"} else 0o644) << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return target


def wheel() -> Path:
    environment = os.environ.copy()
    environment.setdefault(
        "SOURCE_DATE_EPOCH",
        str(int(datetime(2026, 7, 16, tzinfo=timezone.utc).timestamp())),
    )
    subprocess.run(
        [
            sys.executable, "-m", "pip", "wheel", "--disable-pip-version-check",
            "--no-deps", "--wheel-dir", str(OUTPUT), ".",
        ],
        cwd=GATEWAY,
        env=environment,
        check=True,
    )
    wheels = list(OUTPUT.glob("*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"Expected one wheel, found {len(wheels)}")
    return wheels[0]


def sbom(version: str) -> Path:
    metadata = project_metadata()
    components = []
    for requirement in metadata["dependencies"]:
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)(?:\[[^]]+\])?==([^;\s]+)", requirement)
        if not match:
            raise RuntimeError(f"Release dependency must be exactly pinned: {requirement}")
        name, dependency_version = match.groups()
        normalized = name.lower().replace("_", "-")
        components.append(
            {
                "type": "library",
                "name": normalized,
                "version": dependency_version,
                "purl": f"pkg:pypi/{normalized}@{dependency_version}",
            }
        )
    document = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, f'ResearchOS-{version}')}",
        "version": 1,
        "metadata": {
            "timestamp": "2026-07-16T00:00:00Z",
            "component": {
                "type": "application",
                "name": "ResearchOS",
                "version": version,
                "licenses": [{"license": {"id": "Apache-2.0"}}],
                "purl": f"pkg:github/jumadi03/ResearchOS@v{version}",
            },
        },
        "components": sorted(components, key=lambda item: item["name"]),
    }
    target = OUTPUT / f"ResearchOS-{version}.cdx.json"
    target.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def provenance(version: str, subjects: list[Path]) -> Path:
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True
    ).stdout.strip()
    document = {
        "schema_version": "1.0",
        "project": "ResearchOS",
        "version": version,
        "source": {
            "repository": "https://github.com/jumadi03/ResearchOS",
            "revision": revision,
        },
        "builder": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "github_run_id": os.getenv("GITHUB_RUN_ID"),
        },
        "subjects": [
            {"name": path.name, "digest": {"sha256": sha256(path)}}
            for path in sorted(subjects)
        ],
    }
    target = OUTPUT / f"ResearchOS-{version}.provenance.json"
    target.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def checksums() -> Path:
    target = OUTPUT / "SHA256SUMS"
    artifacts = sorted(path for path in OUTPUT.iterdir() if path.is_file() and path != target)
    target.write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in artifacts),
        encoding="utf-8",
    )
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    version = declared_version()
    resolved_output = OUTPUT.resolve()
    if not resolved_output.is_relative_to(ROOT.resolve()) or resolved_output == ROOT.resolve():
        raise RuntimeError("Unsafe release output path")
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir(parents=True)
    built = [wheel(), source_archive(version), sbom(version)]
    built.append(provenance(version, built))
    built.append(checksums())
    print(f"release-build=passed version={version} artifacts={len(built)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
