"""Evidence-bearing, report-only repository verification contracts."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, replace
from datetime import date
from enum import StrEnum
from hashlib import sha256
import json
from pathlib import PurePosixPath

from app.architecture.schema import REPOSITORY_VERIFICATION_SCHEMA


def _valid_hash(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _valid_path(path: str) -> bool:
    item = PurePosixPath(path)
    return bool(
        path
        and "\\" not in path
        and not item.is_absolute()
        and all(part not in {"", ".", ".."} for part in item.parts)
    )


class RepositoryPolicyDomain(StrEnum):
    PLACEMENT = "placement"
    NAMING = "naming"


class RepositoryVerificationOutcome(StrEnum):
    CONFORMS = "conforms"
    FINDING = "finding"
    EXCEPTED = "excepted"
    NOT_EVALUATED = "not_evaluated"


class RepositoryVerificationMode(StrEnum):
    REPORT_ONLY = "report_only"


@dataclass(frozen=True, slots=True)
class RepositoryPolicyEvaluation:
    evaluation_id: str
    file_id: str
    path: str
    content_hash: str
    domain: RepositoryPolicyDomain
    outcome: RepositoryVerificationOutcome
    policy_id: str | None
    policy_version: str | None
    reasons: tuple[str, ...] = ()
    exception_ids: tuple[str, ...] = ()
    evidence_hash: str = ""

    def canonical_payload(self) -> dict[str, object]:
        return {
            key: value for key, value in asdict(
                replace(self, evaluation_id="", evidence_hash="")
            ).items()
            if key not in {"evaluation_id", "evidence_hash"}
        }

    def calculate_evidence_hash(self) -> str:
        return sha256(json.dumps(
            self.canonical_payload(),
            ensure_ascii=False, separators=(",", ":"), sort_keys=True,
        ).encode("utf-8")).hexdigest()

    def finalized(self) -> "RepositoryPolicyEvaluation":
        candidate = replace(
            self,
            evaluation_id="",
            reasons=tuple(sorted(set(self.reasons))),
            exception_ids=tuple(sorted(set(self.exception_ids))),
            evidence_hash="",
        )
        evidence_hash = candidate.calculate_evidence_hash()
        return replace(
            candidate,
            evaluation_id=f"repository-evaluation:{evidence_hash[:24]}",
            evidence_hash=evidence_hash,
        )

    def verify(self) -> bool:
        has_policy = bool(
            self.policy_id
            and self.policy_id.strip()
            and self.policy_version
            and self.policy_version.strip()
        )
        no_policy = self.policy_id is None and self.policy_version is None
        shape_is_valid = {
            RepositoryVerificationOutcome.CONFORMS: (
                has_policy and not self.reasons and not self.exception_ids
            ),
            RepositoryVerificationOutcome.FINDING: (
                has_policy and bool(self.reasons) and not self.exception_ids
            ),
            RepositoryVerificationOutcome.EXCEPTED: (
                has_policy and bool(self.reasons) and bool(self.exception_ids)
            ),
            RepositoryVerificationOutcome.NOT_EVALUATED: (
                no_policy
                and self.reasons == ("no_applicable_policy",)
                and not self.exception_ids
            ),
        }[self.outcome]
        return (
            self.file_id.startswith("file:")
            and _valid_path(self.path)
            and _valid_hash(self.content_hash)
            and all(reason.strip() for reason in self.reasons)
            and all(item.strip() for item in self.exception_ids)
            and shape_is_valid
            and self == self.finalized()
        )


@dataclass(frozen=True, slots=True)
class RepositoryVerificationReport:
    report_id: str
    project_name: str
    source_revision: str
    registry_id: str
    registry_hash: str
    policy_bundle_id: str
    policy_bundle_hash: str
    as_of: str
    evaluations: tuple[RepositoryPolicyEvaluation, ...]
    outcome_counts: tuple[tuple[str, int], ...] = ()
    mode: RepositoryVerificationMode = RepositoryVerificationMode.REPORT_ONLY
    schema_version: str = "1.0"
    content_hash: str = ""

    @property
    def finding_count(self) -> int:
        return sum(
            item.outcome is RepositoryVerificationOutcome.FINDING
            for item in self.evaluations
        )

    @property
    def excepted_count(self) -> int:
        return sum(
            item.outcome is RepositoryVerificationOutcome.EXCEPTED
            for item in self.evaluations
        )

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
            "policy_bundle_id": self.policy_bundle_id,
            "policy_bundle_hash": self.policy_bundle_hash,
            "as_of": self.as_of,
            "evaluations": [
                asdict(item) for item in sorted(
                    self.evaluations, key=lambda item: item.evaluation_id,
                )
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

    def finalized(self) -> "RepositoryVerificationReport":
        evaluations = tuple(sorted(
            self.evaluations, key=lambda item: item.evaluation_id,
        ))
        counts = tuple(sorted(Counter(
            f"{item.domain.value}:{item.outcome.value}"
            for item in evaluations
        ).items()))
        candidate = replace(
            self, report_id="", evaluations=evaluations,
            outcome_counts=counts, content_hash="",
        )
        content_hash = candidate.calculate_content_hash()
        return replace(
            candidate,
            report_id=(
                f"repository-verification:{self.project_name}:"
                f"{content_hash[:16]}"
            ),
            content_hash=content_hash,
        )

    def verify(self) -> bool:
        evaluation_ids = [item.evaluation_id for item in self.evaluations]
        file_domains = [
            (item.file_id, item.domain, item.policy_id)
            for item in self.evaluations
        ]
        try:
            date.fromisoformat(self.as_of)
        except ValueError:
            return False
        return (
            bool(
                self.project_name.strip()
                and self.source_revision.strip()
                and self.registry_id.strip()
                and _valid_hash(self.registry_hash)
                and self.policy_bundle_id.strip()
                and _valid_hash(self.policy_bundle_hash)
                and self.as_of.strip()
                and self.evaluations
            )
            and self.mode is RepositoryVerificationMode.REPORT_ONLY
            and len(evaluation_ids) == len(set(evaluation_ids))
            and len(file_domains) == len(set(file_domains))
            and all(item.verify() for item in self.evaluations)
            and self == self.finalized()
        )

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(
            {
                "report_id": self.report_id,
                "content_hash": self.content_hash,
                "finding_count": self.finding_count,
                "excepted_count": self.excepted_count,
                "is_compliance_decision": self.is_compliance_decision,
                **self.canonical_payload(),
            },
            ensure_ascii=False, indent=indent, sort_keys=True,
        )

    @classmethod
    def from_json(cls, value: str) -> "RepositoryVerificationReport":
        payload = json.loads(value)
        REPOSITORY_VERIFICATION_SCHEMA.require_readable(
            payload.get("schema_version", "")
        )
        report = cls(
            report_id=payload.get("report_id", ""),
            project_name=payload["project_name"],
            source_revision=payload["source_revision"],
            registry_id=payload["registry_id"],
            registry_hash=payload["registry_hash"],
            policy_bundle_id=payload["policy_bundle_id"],
            policy_bundle_hash=payload["policy_bundle_hash"],
            as_of=payload["as_of"],
            evaluations=tuple(
                RepositoryPolicyEvaluation(
                    **{
                        **item,
                        "domain": RepositoryPolicyDomain(item["domain"]),
                        "outcome": RepositoryVerificationOutcome(
                            item["outcome"]
                        ),
                        "reasons": tuple(item.get("reasons", ())),
                        "exception_ids": tuple(
                            item.get("exception_ids", ())
                        ),
                    }
                )
                for item in payload.get("evaluations", ())
            ),
            outcome_counts=tuple(
                (str(item[0]), int(item[1]))
                for item in payload.get("outcome_counts", ())
            ),
            mode=RepositoryVerificationMode(payload.get("mode", "")),
            schema_version=payload.get("schema_version", ""),
            content_hash=payload.get("content_hash", ""),
        )
        if (
            payload.get("finding_count") != report.finding_count
            or payload.get("excepted_count") != report.excepted_count
            or payload.get("is_compliance_decision")
            is not report.is_compliance_decision
            or not report.verify()
        ):
            raise ValueError(
                "Repository verification report identity or content is invalid"
            )
        return report
