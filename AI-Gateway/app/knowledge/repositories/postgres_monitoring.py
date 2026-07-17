"""PostgreSQL adapter for continuous scientific monitoring."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json

from app.knowledge.discovery.normalization import canonical_json
from app.knowledge.monitoring.models import (
    MonitoringRun, ScientificSourceWatch, SourceWatchStatus,
)
from app.knowledge.monitoring.serialization import (
    discovery_run_from_payload, discovery_run_payload,
)


class PostgresMonitoringRepositoryMixin:
    def create_source_watch(
        self, baseline, *, cadence_minutes: int, owner_id: str,
        created_at: str, next_run_at: str, maximum_runs: int | None = None,
        ends_at: str | None = None,
    ):
        baseline.validate_query_plan()
        identity = canonical_json({
            "run_id": baseline.run_id, "owner_id": owner_id,
            "cadence_minutes": cadence_minutes, "created_at": created_at,
        })
        watch = ScientificSourceWatch(
            watch_id=f"watch-{sha256(identity.encode()).hexdigest()[:24]}",
            project_id=baseline.discovery_contract.project_id,
            discovery_contract_id=baseline.discovery_contract.contract_id,
            research_question_id=baseline.question.question_id,
            search_plan_id=baseline.search_plan.plan_id,
            cadence_minutes=cadence_minutes, owner_id=owner_id,
            human_review_policy=baseline.discovery_contract.human_review_policy,
            created_at=created_at, next_run_at=next_run_at,
            maximum_runs=maximum_runs, ends_at=ends_at,
        ).finalized()
        if not watch.verify():
            raise ValueError("Scientific source watch integrity verification failed")
        payload = discovery_run_payload(baseline)
        baseline_hash = sha256(canonical_json(payload).encode()).hexdigest()
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO scientific_source_watches(
                    watch_id,project_id,discovery_contract_id,research_question_id,
                    search_plan_id,cadence_minutes,owner_id,human_review_policy,
                    created_at,maximum_runs,ends_at,definition_hash,schema_version
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(watch_id) DO NOTHING
            """, (
                watch.watch_id, watch.project_id, watch.discovery_contract_id,
                watch.research_question_id, watch.search_plan_id,
                watch.cadence_minutes, watch.owner_id, watch.human_review_policy,
                watch.created_at, watch.maximum_runs, watch.ends_at,
                watch.definition_hash, watch.schema_version,
            ))
            cursor.execute("""
                INSERT INTO scientific_source_watch_state(
                    watch_id,status,next_run_at,completed_runs,
                    baseline_discovery_run,baseline_hash
                ) VALUES (%s,'active',%s,0,%s,%s)
                ON CONFLICT(watch_id) DO NOTHING
            """, (watch.watch_id, watch.next_run_at, json.dumps(payload), baseline_hash))
        return watch

    def load_source_watch(self, watch_id: str):
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("""
                SELECT w.watch_id,w.project_id,w.discovery_contract_id,
                    w.research_question_id,w.search_plan_id,w.cadence_minutes,
                    w.owner_id,w.human_review_policy,w.created_at,s.next_run_at,
                    s.status,w.maximum_runs,w.ends_at,s.completed_runs,
                    w.definition_hash,w.schema_version,s.baseline_discovery_run
                FROM scientific_source_watches w
                JOIN scientific_source_watch_state s USING(watch_id)
                WHERE w.watch_id=%s
            """, (watch_id,))
            row = cursor.fetchone()
        if row is None:
            raise KeyError(f"Unknown scientific source watch: {watch_id}")
        watch = ScientificSourceWatch(
            watch_id=row[0], project_id=row[1],
            discovery_contract_id=row[2], research_question_id=row[3],
            search_plan_id=row[4], cadence_minutes=row[5], owner_id=row[6],
            human_review_policy=row[7], created_at=str(row[8]),
            next_run_at=str(row[9]), status=SourceWatchStatus(row[10]),
            maximum_runs=row[11], ends_at=str(row[12]) if row[12] else None,
            completed_runs=row[13], definition_hash=row[14],
            schema_version=row[15],
        )
        if not watch.verify():
            raise ValueError("Canonical source watch integrity verification failed")
        return watch, discovery_run_from_payload(row[16])

    def list_source_watches(self, project_id: str):
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("""
                SELECT watch_id FROM scientific_source_watches
                WHERE project_id=%s ORDER BY created_at,watch_id
            """, (project_id,))
            ids = tuple(row[0] for row in cursor.fetchall())
        return tuple(self.load_source_watch(item)[0] for item in ids)

    def persist_monitoring_run(self, watch, run: MonitoringRun, current) -> None:
        if not watch.verify() or not run.verify() or run.watch_id != watch.watch_id:
            raise ValueError("Monitoring persistence integrity verification failed")
        payload = discovery_run_payload(current)
        baseline_hash = sha256(canonical_json(payload).encode()).hexdigest()
        next_run = (
            datetime.fromisoformat(run.scheduled_at.replace("Z", "+00:00"))
            + timedelta(minutes=watch.cadence_minutes)
        ).astimezone(timezone.utc).isoformat()
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("""
                SELECT status,next_run_at,completed_runs
                FROM scientific_source_watch_state
                WHERE watch_id=%s FOR UPDATE
            """, (watch.watch_id,))
            state = cursor.fetchone()
            if state is None or state[0] != "active":
                raise ValueError("Scientific source watch is not active")
            cursor.execute("""
                INSERT INTO scientific_monitoring_runs(
                    monitoring_run_id,watch_id,scheduled_at,started_at,completed_at,
                    previous_discovery_run_id,current_discovery_run_id,
                    provider_failures,stopping_reason,manifest_hash,schema_version
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(monitoring_run_id) DO NOTHING
                RETURNING manifest_hash
            """, (
                run.monitoring_run_id, run.watch_id, run.scheduled_at,
                run.started_at, run.completed_at, run.previous_discovery_run_id,
                run.current_discovery_run_id, json.dumps(run.provider_failures),
                run.stopping_reason, run.manifest_hash, run.schema_version,
            ))
            inserted = cursor.fetchone()
            if inserted is None:
                cursor.execute("""
                    SELECT manifest_hash FROM scientific_monitoring_runs
                    WHERE monitoring_run_id=%s
                """, (run.monitoring_run_id,))
                existing = cursor.fetchone()
                if existing is None or existing[0] != run.manifest_hash:
                    raise ValueError("Monitoring run persistence integrity conflict")
                return
            for change in run.changes:
                cursor.execute("""
                    INSERT INTO scientific_changes(
                        change_id,monitoring_run_id,change_kind,record_key,provider,
                        before_hash,after_hash,details
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(change_id) DO NOTHING
                """, (
                    change.change_id, run.monitoring_run_id, change.kind.value,
                    change.record_key, change.provider, change.before_hash,
                    change.after_hash, json.dumps(dict(change.details)),
                ))
            completed = state[2] + 1
            expired = (
                (watch.maximum_runs is not None and completed >= watch.maximum_runs)
                or (
                    watch.ends_at is not None
                    and datetime.fromisoformat(next_run.replace("Z", "+00:00"))
                    > datetime.fromisoformat(watch.ends_at.replace("Z", "+00:00"))
                )
            )
            cursor.execute("""
                UPDATE scientific_source_watch_state SET
                    status=%s,next_run_at=%s,completed_runs=%s,
                    baseline_discovery_run=%s,baseline_hash=%s,updated_at=now()
                WHERE watch_id=%s
            """, (
                "expired" if expired else "active", next_run, completed,
                json.dumps(payload), baseline_hash, watch.watch_id,
            ))

    def acknowledge_scientific_change(
        self, change_id: str, *, actor_id: str, rationale: str, occurred_at: str,
    ) -> str:
        if not actor_id.strip() or not rationale.strip():
            raise ValueError("Acknowledgement actor and rationale are required")
        identity = canonical_json({
            "change_id": change_id, "actor_id": actor_id,
            "rationale": rationale, "occurred_at": occurred_at,
        })
        ack_id = f"ack-{sha256(identity.encode()).hexdigest()[:24]}"
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO scientific_change_acknowledgements(
                    acknowledgement_id,change_id,actor_id,rationale,occurred_at
                ) VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT(acknowledgement_id) DO NOTHING
            """, (ack_id, change_id, actor_id, rationale.strip(), occurred_at))
        return ack_id
