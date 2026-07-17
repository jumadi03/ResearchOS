"""Report-only placement and naming verification for FMA-004."""

from __future__ import annotations

from datetime import date
import re
from pathlib import PurePosixPath

from .file_registry_models import RepositoryFileEntry, RepositoryFileRegistry
from .policy_models import (
    RepositoryNamingPolicy,
    RepositoryPlacementPolicy,
    RepositoryPolicyException,
)
from .policy_registry import RepositoryPolicyRegistry
from .verification_models import (
    RepositoryPolicyDomain,
    RepositoryPolicyEvaluation,
    RepositoryVerificationOutcome,
    RepositoryVerificationReport,
)


class RepositoryPlacementNamingVerifier:
    @staticmethod
    def _validate_inputs(
        registry: RepositoryFileRegistry,
        policies: RepositoryPolicyRegistry,
        as_of: str,
    ) -> date:
        if not registry.verify():
            raise ValueError("Repository file registry integrity verification failed")
        if not policies.bundle.verify():
            raise ValueError("Repository policy integrity verification failed")
        if registry.project_name != policies.bundle.project_name:
            raise ValueError("Registry and policy project do not match")
        if (
            registry.policy_bundle_id != policies.bundle.bundle_id
            or registry.policy_bundle_hash != policies.bundle.content_hash
        ):
            raise ValueError("Registry and policy provenance do not match")
        try:
            return date.fromisoformat(as_of)
        except ValueError as exc:
            raise ValueError("Verification as_of must be an ISO date") from exc

    @staticmethod
    def _active_exceptions(
        exceptions: tuple[RepositoryPolicyException, ...],
        as_of: date,
    ) -> tuple[RepositoryPolicyException, ...]:
        return tuple(
            item for item in exceptions
            if date.fromisoformat(item.approved_at) <= as_of
            and (
                item.expires_at is None
                or as_of <= date.fromisoformat(item.expires_at)
            )
        )

    @staticmethod
    def _evaluation(
        entry: RepositoryFileEntry,
        domain: RepositoryPolicyDomain,
        policy: RepositoryPlacementPolicy | RepositoryNamingPolicy | None,
        reasons: tuple[str, ...],
        exceptions: tuple[RepositoryPolicyException, ...] = (),
    ) -> RepositoryPolicyEvaluation:
        if policy is None:
            outcome = RepositoryVerificationOutcome.NOT_EVALUATED
        elif not reasons:
            outcome = RepositoryVerificationOutcome.CONFORMS
        elif exceptions:
            outcome = RepositoryVerificationOutcome.EXCEPTED
        else:
            outcome = RepositoryVerificationOutcome.FINDING
        return RepositoryPolicyEvaluation(
            evaluation_id="",
            file_id=entry.file_id,
            path=entry.current_path,
            content_hash=entry.content_hash,
            domain=domain,
            outcome=outcome,
            policy_id=policy.policy_id if policy else None,
            policy_version=policy.version if policy else None,
            reasons=reasons,
            exception_ids=tuple(item.exception_id for item in exceptions),
        ).finalized()

    def verify(
        self,
        registry: RepositoryFileRegistry,
        policies: RepositoryPolicyRegistry,
        *,
        as_of: str,
    ) -> RepositoryVerificationReport:
        evaluation_date = self._validate_inputs(registry, policies, as_of)
        evaluations = []
        for entry in registry.entries:
            applicable = policies.resolve(entry.current_path)
            placement = tuple(
                item for item in applicable
                if isinstance(item, RepositoryPlacementPolicy)
            )
            naming = tuple(
                item for item in applicable
                if isinstance(item, RepositoryNamingPolicy)
            )
            if not placement:
                evaluations.append(self._evaluation(
                    entry, RepositoryPolicyDomain.PLACEMENT, None,
                    ("no_applicable_policy",),
                ))
            for policy in placement:
                reasons = []
                if entry.classification not in policy.allowed_classifications:
                    reasons.append("classification_not_allowed")
                if (
                    policy.allowed_extensions
                    and entry.extension not in policy.allowed_extensions
                ):
                    reasons.append("extension_not_allowed")
                if entry.extension in policy.forbidden_extensions:
                    reasons.append("extension_forbidden")
                exceptions = self._active_exceptions(
                    policies.resolve_exceptions(
                        entry.current_path, (policy.policy_id,),
                    ),
                    evaluation_date,
                )
                evaluations.append(self._evaluation(
                    entry, RepositoryPolicyDomain.PLACEMENT, policy,
                    tuple(reasons), exceptions if reasons else (),
                ))

            if not naming:
                evaluations.append(self._evaluation(
                    entry, RepositoryPolicyDomain.NAMING, None,
                    ("no_applicable_policy",),
                ))
            for policy in naming:
                reasons = (
                    ()
                    if re.fullmatch(
                        policy.name_pattern,
                        PurePosixPath(entry.current_path).name,
                    )
                    else ("name_pattern_mismatch",)
                )
                exceptions = self._active_exceptions(
                    policies.resolve_exceptions(
                        entry.current_path, (policy.policy_id,),
                    ),
                    evaluation_date,
                )
                evaluations.append(self._evaluation(
                    entry, RepositoryPolicyDomain.NAMING, policy,
                    reasons, exceptions if reasons else (),
                ))

        report = RepositoryVerificationReport(
            report_id="",
            project_name=registry.project_name,
            source_revision=registry.source_revision,
            registry_id=registry.registry_id,
            registry_hash=registry.content_hash,
            policy_bundle_id=policies.bundle.bundle_id,
            policy_bundle_hash=policies.bundle.content_hash,
            as_of=as_of,
            evaluations=tuple(evaluations),
        ).finalized()
        if not report.verify():
            raise ValueError(
                "Repository verification report integrity verification failed"
            )
        return report
