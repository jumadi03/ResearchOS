"""Content-addressed, report-only repository health contracts."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, replace
from datetime import date
from enum import StrEnum
from hashlib import sha256
import json
from pathlib import PurePosixPath

from app.architecture.schema import REPOSITORY_HEALTH_SCHEMA


def _valid_hash(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _valid_repository_path(value: str) -> bool:
    if not value or "\\" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts and "." not in path.parts


class RepositoryHealthCategory(StrEnum):
    CANONICAL_LEAKAGE = "canonical_leakage"
    UNKNOWN_CLASSIFICATION = "unknown_classification"
    GOVERNANCE_COVERAGE = "governance_coverage"
    POLICY_FINDINGS = "policy_findings"
    POLICY_COVERAGE = "policy_coverage"
    POLICY_EXCEPTIONS = "policy_exceptions"
    NON_EMPTY_EXACT_DUPLICATION = "non_empty_exact_duplication"
    CAPABILITY_TEST_PRESENCE = "capability_test_presence"
    DEAD_FILE_ANALYSIS = "dead_file_analysis"
    STALENESS = "staleness"
    EXECUTION_COVERAGE = "execution_coverage"
    DOCUMENTATION_COVERAGE = "documentation_coverage"


class RepositoryHealthOutcome(StrEnum):
    OBSERVED = "observed"
    FINDING = "finding"
    ADVISORY = "advisory"
    NOT_EVALUATED = "not_evaluated"


@dataclass(frozen=True, slots=True)
class RepositoryHealthCheck:
    check_id: str
    category: RepositoryHealthCategory
    outcome: RepositoryHealthOutcome
    summary: str
    affected_file_ids: tuple[str, ...] = ()
    affected_paths: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    details: dict[str, object] | None = None
    evidence_hash: str = ""

    def canonical_payload(self) -> dict[str, object]:
        return {
            key: value for key, value in asdict(
                replace(self, check_id="", evidence_hash="")
            ).items()
            if key not in {"check_id", "evidence_hash"}
        }

    def calculate_evidence_hash(self) -> str:
        return sha256(json.dumps(
            self.canonical_payload(),
            ensure_ascii=False, separators=(",", ":"), sort_keys=True,
        ).encode("utf-8")).hexdigest()

    def finalized(self) -> "RepositoryHealthCheck":
        pairs = tuple(sorted(set(zip(
            self.affected_file_ids, self.affected_paths,
        ))))
        candidate = replace(
            self,
            check_id="",
            affected_file_ids=tuple(item[0] for item in pairs),
            affected_paths=tuple(item[1] for item in pairs),
            evidence_ids=tuple(sorted(set(self.evidence_ids))),
            details=self.details or {},
            evidence_hash="",
        )
        evidence_hash = candidate.calculate_evidence_hash()
        return replace(
            candidate,
            check_id=f"repository-health-check:{evidence_hash[:24]}",
            evidence_hash=evidence_hash,
        )

    def verify(self) -> bool:
        affected = bool(self.affected_file_ids or self.affected_paths)
        outcome_shape = {
            RepositoryHealthOutcome.OBSERVED: not affected,
            RepositoryHealthOutcome.FINDING: affected,
            RepositoryHealthOutcome.ADVISORY: affected,
            RepositoryHealthOutcome.NOT_EVALUATED: (
                not affected
                and bool((self.details or {}).get("reason"))
            ),
        }[self.outcome]
        return (
            bool(self.summary.strip())
            and len(self.affected_file_ids) == len(self.affected_paths)
            and all(item.startswith("file:") for item in self.affected_file_ids)
            and all(_valid_repository_path(path) for path in self.affected_paths)
            and all(item.strip() for item in self.evidence_ids)
            and outcome_shape
            and self == self.finalized()
        )


@dataclass(frozen=True, slots=True)
class RepositoryHealthReport:
    report_id: str
    project_name: str
    source_revision: str
    registry_id: str
    registry_hash: str
    verification_report_id: str
    verification_report_hash: str
    graph_id: str
    graph_hash: str
    as_of: str
    checks: tuple[RepositoryHealthCheck, ...]
    outcome_counts: tuple[tuple[str, int], ...] = ()
    mode: str = "report_only"
    schema_version: str = "1.0"
    content_hash: str = ""

    @property
    def status(self) -> str:
        outcomes = {item.outcome for item in self.checks}
        if RepositoryHealthOutcome.NOT_EVALUATED in outcomes:
            return "INCOMPLETE"
        if RepositoryHealthOutcome.FINDING in outcomes:
            return "FINDINGS"
        return "OBSERVED"

    @property
    def is_compliance_decision(self) -> bool:
        return False

    def canonical_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "mode": self.mode,
            "project_name": self.project_name,
            "source_revision": self.source_revision,
            "registry_id": self.registry_id,
            "registry_hash": self.registry_hash,
            "verification_report_id": self.verification_report_id,
            "verification_report_hash": self.verification_report_hash,
            "graph_id": self.graph_id,
            "graph_hash": self.graph_hash,
            "as_of": self.as_of,
            "checks": [
                asdict(item)
                for item in sorted(self.checks, key=lambda item: item.check_id)
            ],
            "outcome_counts": [
                list(item) for item in sorted(self.outcome_counts)
            ],
        }

    def calculate_content_hash(self) -> str:
        return sha256(json.dumps(
            self.canonical_payload(),
            ensure_ascii=False, separators=(",", ":"), sort_keys=True,
        ).encode("utf-8")).hexdigest()

    def finalized(self) -> "RepositoryHealthReport":
        checks = tuple(sorted(self.checks, key=lambda item: item.check_id))
        counts = tuple(sorted(Counter(
            item.outcome.value for item in checks
        ).items()))
        candidate = replace(
            self, report_id="", checks=checks, outcome_counts=counts,
            content_hash="",
        )
        content_hash = candidate.calculate_content_hash()
        return replace(
            candidate,
            report_id=f"repository-health:{self.project_name}:{content_hash[:16]}",
            content_hash=content_hash,
        )

    def verify(self) -> bool:
        try:
            date.fromisoformat(self.as_of)
        except ValueError:
            return False
        categories = [item.category for item in self.checks]
        check_ids = [item.check_id for item in self.checks]
        return (
            bool(
                self.project_name.strip()
                and self.source_revision.strip()
                and self.registry_id.strip()
                and _valid_hash(self.registry_hash)
                and self.verification_report_id.strip()
                and _valid_hash(self.verification_report_hash)
                and self.graph_id.strip()
                and _valid_hash(self.graph_hash)
            )
            and self.mode == "report_only"
            and set(categories) == set(RepositoryHealthCategory)
            and len(categories) == len(set(categories))
            and len(check_ids) == len(set(check_ids))
            and all(item.verify() for item in self.checks)
            and self == self.finalized()
        )

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(
            {
                "report_id": self.report_id,
                "content_hash": self.content_hash,
                "status": self.status,
                "is_compliance_decision": self.is_compliance_decision,
                **self.canonical_payload(),
            },
            ensure_ascii=False, indent=indent, sort_keys=True,
        )

    @classmethod
    def from_json(cls, value: str) -> "RepositoryHealthReport":
        payload = json.loads(value)
        REPOSITORY_HEALTH_SCHEMA.require_readable(
            payload.get("schema_version", "")
        )
        report = cls(
            report_id=payload.get("report_id", ""),
            project_name=payload["project_name"],
            source_revision=payload["source_revision"],
            registry_id=payload["registry_id"],
            registry_hash=payload["registry_hash"],
            verification_report_id=payload["verification_report_id"],
            verification_report_hash=payload["verification_report_hash"],
            graph_id=payload["graph_id"],
            graph_hash=payload["graph_hash"],
            as_of=payload["as_of"],
            checks=tuple(
                RepositoryHealthCheck(
                    **{
                        **item,
                        "category": RepositoryHealthCategory(item["category"]),
                        "outcome": RepositoryHealthOutcome(item["outcome"]),
                        "affected_file_ids": tuple(
                            item.get("affected_file_ids", ())
                        ),
                        "affected_paths": tuple(
                            item.get("affected_paths", ())
                        ),
                        "evidence_ids": tuple(item.get("evidence_ids", ())),
                    }
                )
                for item in payload.get("checks", ())
            ),
            outcome_counts=tuple(
                (str(item[0]), int(item[1]))
                for item in payload.get("outcome_counts", ())
            ),
            mode=payload.get("mode", ""),
            schema_version=payload.get("schema_version", ""),
            content_hash=payload.get("content_hash", ""),
        )
        if (
            payload.get("status") != report.status
            or payload.get("is_compliance_decision")
            is not report.is_compliance_decision
            or not report.verify()
        ):
            raise ValueError("Repository health report identity or content is invalid")
        return report
