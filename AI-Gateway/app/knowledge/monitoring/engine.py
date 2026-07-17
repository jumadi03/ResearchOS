"""Deterministic change detection between canonical discovery baselines."""

from __future__ import annotations

from hashlib import sha256

from app.knowledge.discovery.normalization import canonical_json
from app.knowledge.models import DiscoveryRun, LiteratureRecord
from app.knowledge.monitoring.models import (
    MonitoringRun, ScientificChange, ScientificChangeKind,
    ScientificSourceWatch,
)


def _record_key(record: LiteratureRecord) -> str:
    if record.doi:
        return f"doi:{record.doi.casefold()}"
    identifiers = sorted(
        f"{item.provider}:{item.source_id.casefold()}"
        for item in record.source_records
    )
    return identifiers[0] if identifiers else f"record:{record.record_id}"


def _metadata(record: LiteratureRecord) -> dict:
    return {
        "title": record.title, "authors": record.authors, "year": record.year,
        "doi": record.doi, "abstract": record.abstract, "venue": record.venue,
        "work_type": record.work_type,
    }


def _citation_state(record: LiteratureRecord) -> dict:
    values = {}
    for source in record.source_records:
        raw = source.raw
        values[source.provider] = {
            "citation_count": (
                raw.get("cited_by_count")
                if source.provider == "openalex"
                else raw.get("citationCount")
                if source.provider == "semantic_scholar"
                else raw.get("is-referenced-by-count")
            ),
            "references": (
                raw.get("referenced_works")
                or raw.get("references")
                or raw.get("reference")
                or ()
            ),
        }
    return values


def _lifecycle(record: LiteratureRecord) -> tuple[bool, bool]:
    retracted = any(
        bool(source.raw.get("is_retracted"))
        for source in record.source_records
    )
    corrected = any(
        any(key in (source.raw.get("relation") or {}) for key in (
            "is-corrected-by", "is-updated-by",
        ))
        for source in record.source_records
    )
    return corrected, retracted


def _digest(value) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


class ScientificMonitoringEngine:
    def compare(
        self, watch: ScientificSourceWatch, previous: DiscoveryRun,
        current: DiscoveryRun, *, scheduled_at: str, started_at: str,
        completed_at: str,
    ) -> MonitoringRun:
        if not watch.verify():
            raise ValueError("Scientific source watch integrity verification failed")
        for run in (previous, current):
            run.validate_query_plan()
            if (
                run.discovery_contract.contract_id != watch.discovery_contract_id
                or run.question.question_id != watch.research_question_id
                or run.search_plan.plan_id != watch.search_plan_id
            ):
                raise ValueError("Monitoring run does not match source watch contract")
        if (
            current.question != previous.question
            or current.discovery_contract != previous.discovery_contract
            or current.search_plan != previous.search_plan
            or current.source_definitions != previous.source_definitions
        ):
            raise ValueError("Monitoring run attempted to expand or alter watch scope")

        before = {_record_key(item): item for item in previous.records}
        after = {_record_key(item): item for item in current.records}
        changes = []
        for key in sorted(after.keys() - before.keys()):
            record = after[key]
            changes.append(self._change(
                watch, key, ScientificChangeKind.NEW_CANDIDATE, None,
                _digest(_metadata(record)), None,
            ))
        for key in sorted(before.keys() & after.keys()):
            old, new = before[key], after[key]
            old_metadata, new_metadata = _metadata(old), _metadata(new)
            old_hash, new_hash = _digest(old_metadata), _digest(new_metadata)
            if old_hash != new_hash:
                changes.append(self._change(
                    watch, key, ScientificChangeKind.METADATA_CHANGED,
                    old_hash, new_hash, None,
                ))
            old_citations, new_citations = (
                _citation_state(old), _citation_state(new),
            )
            old_citation_hash, new_citation_hash = (
                _digest(old_citations), _digest(new_citations),
            )
            if old_citation_hash != new_citation_hash:
                changes.append(self._change(
                    watch, key, ScientificChangeKind.CITATION_CHANGED,
                    old_citation_hash, new_citation_hash, None,
                ))
            old_corrected, old_retracted = _lifecycle(old)
            corrected, retracted = _lifecycle(new)
            if corrected and not old_corrected:
                changes.append(self._change(
                    watch, key, ScientificChangeKind.CORRECTED,
                    old_hash, new_hash, None,
                ))
            if retracted and not old_retracted:
                changes.append(self._change(
                    watch, key, ScientificChangeKind.RETRACTED,
                    old_hash, new_hash, None,
                ))
        for failure in current.failures:
            details = (
                ("error_type", failure.error_type),
                ("message", failure.message),
            )
            changes.append(self._change(
                watch, f"provider:{failure.provider}",
                ScientificChangeKind.PROVIDER_FAILURE, None, None,
                failure.provider, details,
            ))
        identity = canonical_json({
            "watch_id": watch.watch_id, "scheduled_at": scheduled_at,
            "current_discovery_run_id": current.run_id,
        })
        result = MonitoringRun(
            f"monitoring-{sha256(identity.encode()).hexdigest()[:24]}",
            watch.watch_id, scheduled_at, started_at, completed_at,
            previous.run_id, current.run_id,
            tuple(sorted(changes, key=lambda item: item.change_id)),
            tuple(
                (item.provider, item.error_type, item.retryable)
                for item in current.failures
            ),
            "partial_provider_failure" if current.failures else "complete",
        ).finalized()
        if not result.verify():
            raise ValueError("Monitoring manifest integrity verification failed")
        return result

    @staticmethod
    def _change(
        watch, key, kind, before_hash, after_hash, provider,
        details=(),
    ):
        identity = canonical_json({
            "watch_id": watch.watch_id, "record_key": key,
            "kind": kind.value, "before_hash": before_hash,
            "after_hash": after_hash, "provider": provider,
        })
        return ScientificChange(
            f"change-{sha256(identity.encode()).hexdigest()[:24]}",
            kind, key, provider, before_hash, after_hash, tuple(details),
        )
