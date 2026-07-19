"""PostgreSQL adapter for continuous scientific monitoring."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json

from app.knowledge.discovery.normalization import canonical_json
from app.knowledge.monitoring.models import (
    MonitoringRun, ScientificSourceWatch, SourceWatchStatus,
    SourceWatchTransition,
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

    def transition_source_watch(
        self, watch_id: str, *, to_status: str, actor_id: str,
        rationale: str, occurred_at: str, next_run_at: str | None = None,
    ):
        target = SourceWatchStatus(to_status)
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("""
                SELECT s.status,w.owner_id
                FROM scientific_source_watch_state s
                JOIN scientific_source_watches w USING(watch_id)
                WHERE s.watch_id=%s FOR UPDATE OF s
            """, (watch_id,))
            row = cursor.fetchone()
            if row is None:
                raise KeyError(f"Unknown scientific source watch: {watch_id}")
            if row[1] != actor_id:
                raise PermissionError(
                    "Only the scientific source watch owner may change its lifecycle"
                )
            current = SourceWatchStatus(row[0])
            identity = canonical_json({
                "watch_id": watch_id, "from_status": current.value,
                "to_status": target.value, "actor_id": actor_id,
                "rationale": rationale, "occurred_at": occurred_at,
                "next_run_at": next_run_at,
            })
            transition = SourceWatchTransition(
                f"watch-transition-{sha256(identity.encode()).hexdigest()[:24]}",
                watch_id, current, target, actor_id, rationale.strip(),
                occurred_at, next_run_at,
            )
            if not transition.verify():
                raise ValueError("Scientific source watch transition is invalid")
            cursor.execute("""
                INSERT INTO scientific_source_watch_transitions(
                    transition_id,watch_id,from_status,to_status,actor_id,
                    rationale,occurred_at,next_run_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(transition_id) DO NOTHING
            """, (
                transition.transition_id, transition.watch_id,
                transition.from_status.value, transition.to_status.value,
                transition.actor_id, transition.rationale,
                transition.occurred_at, transition.next_run_at,
            ))
            cursor.execute("""
                UPDATE scientific_source_watch_state SET status=%s,
                    next_run_at=CASE WHEN %s::timestamptz IS NULL
                        THEN next_run_at ELSE %s::timestamptz END,
                    updated_at=now()
                WHERE watch_id=%s
            """, (target.value, next_run_at, next_run_at, watch_id))
        return transition

    def list_monitoring_runs(self, watch_id: str):
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("""
                SELECT monitoring_run_id,watch_id,scheduled_at,started_at,
                    completed_at,previous_discovery_run_id,
                    current_discovery_run_id,provider_failures,
                    stopping_reason,manifest_hash,schema_version
                FROM scientific_monitoring_runs WHERE watch_id=%s
                ORDER BY scheduled_at DESC,monitoring_run_id
            """, (watch_id,))
            return tuple({
                "monitoring_run_id": row[0], "watch_id": row[1],
                "scheduled_at": str(row[2]), "started_at": str(row[3]),
                "completed_at": str(row[4]),
                "previous_discovery_run_id": row[5],
                "current_discovery_run_id": row[6],
                "provider_failures": row[7], "stopping_reason": row[8],
                "manifest_hash": row[9], "schema_version": row[10],
            } for row in cursor.fetchall())

    def list_scientific_changes(
        self, watch_id: str, *, unacknowledged_only: bool = False,
    ):
        condition = (
            "AND NOT EXISTS(SELECT 1 FROM scientific_change_acknowledgements "
            "a WHERE a.change_id=c.change_id)"
            if unacknowledged_only else ""
        )
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT c.change_id,c.monitoring_run_id,c.change_kind,
                    c.record_key,c.provider,c.before_hash,c.after_hash,c.details,
                    EXISTS(
                        SELECT 1 FROM scientific_change_acknowledgements a
                        WHERE a.change_id=c.change_id
                    ) AS acknowledged
                FROM scientific_changes c
                JOIN scientific_monitoring_runs r
                    ON r.monitoring_run_id=c.monitoring_run_id
                WHERE r.watch_id=%s {condition}
                ORDER BY r.scheduled_at DESC,c.change_id
            """, (watch_id,))
            return tuple({
                "change_id": row[0], "monitoring_run_id": row[1],
                "kind": row[2], "record_key": row[3], "provider": row[4],
                "before_hash": row[5], "after_hash": row[6],
                "details": row[7], "acknowledged": row[8],
                "candidate_status": "discovery_only",
            } for row in cursor.fetchall())

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
            cursor.execute(
                "SELECT 1 FROM scientific_changes WHERE change_id=%s",
                (change_id,),
            )
            if cursor.fetchone() is None:
                raise KeyError(f"Unknown scientific change: {change_id}")
            cursor.execute("""
                INSERT INTO scientific_change_acknowledgements(
                    acknowledgement_id,change_id,actor_id,rationale,occurred_at
                ) VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT(acknowledgement_id) DO NOTHING
            """, (ack_id, change_id, actor_id, rationale.strip(), occurred_at))
        return ack_id

    def resolve_impact_review(
        self, change_id: str, *, decision: str, reviewer_id: str,
        rationale: str, occurred_at: str,
    ):
        from app.knowledge.monitoring.models import (
            ImpactReviewDecision, ImpactReviewResolution,
        )
        selected = ImpactReviewDecision(decision)
        if not reviewer_id.strip() or not rationale.strip():
            raise ValueError("Impact review reviewer and rationale are required")
        identity = canonical_json({
            "change_id": change_id, "decision": selected.value,
            "reviewer_id": reviewer_id, "rationale": rationale.strip(),
            "occurred_at": occurred_at,
        })
        resolution_id = f"impact-resolution-{sha256(identity.encode()).hexdigest()[:24]}"
        payload = {
            "resolution_id": resolution_id, "change_id": change_id,
            "decision": selected.value, "reviewer_id": reviewer_id,
            "rationale": rationale.strip(), "occurred_at": occurred_at,
        }
        event_hash = sha256(canonical_json(payload).encode()).hexdigest()
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("""
                SELECT c.change_kind
                FROM scientific_changes c
                WHERE c.change_id=%s
            """, (change_id,))
            row = cursor.fetchone()
            if row is None:
                raise KeyError(f"Unknown scientific change: {change_id}")
            if row[0] != "retracted":
                raise ValueError("Impact review resolution requires a retraction signal")
            cursor.execute("""
                SELECT resolution_id,decision,reviewer_id,rationale,occurred_at,
                       provenance_id
                FROM scientific_impact_review_resolutions
                WHERE change_id=%s
            """, (change_id,))
            existing = cursor.fetchone()
            if existing is not None:
                if existing[0] != resolution_id:
                    raise ValueError("Impact review has already been resolved")
                return ImpactReviewResolution(
                    existing[0], change_id, ImpactReviewDecision(existing[1]),
                    existing[2], existing[3],
                    existing[4].isoformat().replace("+00:00", "Z"),
                    str(existing[5]),
                )
            cursor.execute("""
                INSERT INTO provenance_events(
                    execution_id,human_reviewer,event_type,event_payload,
                    occurred_at,event_hash
                ) VALUES (%s,%s,'scientific_impact_review_resolution',%s,%s,%s)
                RETURNING provenance_id
            """, (
                resolution_id, reviewer_id, json.dumps(payload),
                occurred_at, event_hash,
            ))
            provenance_id = cursor.fetchone()[0]
            cursor.execute("""
                INSERT INTO scientific_impact_review_resolutions(
                    resolution_id,change_id,decision,reviewer_id,rationale,
                    occurred_at,provenance_id
                ) VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (
                resolution_id, change_id, selected.value, reviewer_id,
                rationale.strip(), occurred_at, provenance_id,
            ))
        return ImpactReviewResolution(
            resolution_id, change_id, selected, reviewer_id,
            rationale.strip(), occurred_at, str(provenance_id),
        )

    def select_follow_up_target(
        self, resolution_id: str, *, target_kind: str, target_object_id: str,
        selector_id: str, rationale: str, occurred_at: str,
    ):
        from app.knowledge.monitoring.models import FollowUpCaseTarget
        if target_kind not in {"evidence", "publication"}:
            raise ValueError("Invalid follow-up target kind")
        if not selector_id.strip() or not rationale.strip():
            raise ValueError("Target selector and rationale are required")
        identity = canonical_json({
            "resolution_id": resolution_id, "target_kind": target_kind,
            "target_object_id": target_object_id, "selector_id": selector_id,
            "rationale": rationale.strip(), "occurred_at": occurred_at,
        })
        selection_id = f"follow-up-target-{sha256(identity.encode()).hexdigest()[:24]}"
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("""
                SELECT decision FROM scientific_impact_review_resolutions
                WHERE resolution_id=%s
            """, (resolution_id,))
            row = cursor.fetchone()
            if row is None:
                raise KeyError(f"Unknown impact resolution: {resolution_id}")
            expected = (
                "evidence" if row[0] == "evidence_review_required"
                else "publication" if row[0] == "publication_review_required"
                else None
            )
            if expected != target_kind:
                raise ValueError("Follow-up target kind does not match impact decision")
            if target_kind == "evidence":
                cursor.execute("""
                    SELECT c.object_id FROM canonical_objects c
                    JOIN evidence_objects e ON e.evidence_id=c.object_id
                    WHERE c.object_id::text=%s OR c.stable_key=%s
                """, (target_object_id, f"evidence:{target_object_id}"))
            else:
                cursor.execute("""
                    SELECT c.object_id FROM canonical_objects c
                    JOIN research_artifacts a ON a.artifact_id=c.object_id
                    WHERE (c.object_id::text=%s OR c.stable_key=%s)
                      AND a.artifact_type='publication_package'
                """, (target_object_id, f"artifact:{target_object_id}"))
            target = cursor.fetchone()
            if target is None:
                raise KeyError(f"Unknown canonical {target_kind}: {target_object_id}")
            canonical_id = target[0]
            payload = {
                "selection_id": selection_id,
                "source_resolution_id": resolution_id,
                "target_kind": target_kind,
                "target_object_id": target_object_id,
                "selector_id": selector_id, "rationale": rationale.strip(),
                "occurred_at": occurred_at,
            }
            event_hash = sha256(canonical_json(payload).encode()).hexdigest()
            cursor.execute("""
                INSERT INTO provenance_events(
                    execution_id,output_object_id,human_reviewer,event_type,
                    event_payload,occurred_at,event_hash
                ) VALUES (%s,%s,%s,'follow_up_case_target_selected',%s,%s,%s)
                ON CONFLICT(event_hash) DO NOTHING RETURNING provenance_id
            """, (
                selection_id, canonical_id, selector_id, json.dumps(payload),
                occurred_at, event_hash,
            ))
            inserted = cursor.fetchone()
            if inserted is None:
                cursor.execute(
                    "SELECT provenance_id FROM provenance_events WHERE event_hash=%s",
                    (event_hash,),
                )
                provenance_id = cursor.fetchone()[0]
            else:
                provenance_id = inserted[0]
            cursor.execute("""
                INSERT INTO scientific_follow_up_case_targets(
                    selection_id,resolution_id,target_kind,target_object_id,
                    selector_id,rationale,occurred_at,provenance_id
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(resolution_id) DO NOTHING
                RETURNING selection_id
            """, (
                selection_id, resolution_id, target_kind, canonical_id,
                selector_id, rationale.strip(), occurred_at, provenance_id,
            ))
            linked = cursor.fetchone()
            if linked is None:
                cursor.execute("""
                    SELECT selection_id FROM scientific_follow_up_case_targets
                    WHERE resolution_id=%s
                """, (resolution_id,))
                if cursor.fetchone()[0] != selection_id:
                    raise ValueError("Follow-up case target has already been selected")
        return FollowUpCaseTarget(
            selection_id, resolution_id, target_kind, target_object_id,
            selector_id, rationale.strip(), occurred_at, str(provenance_id),
        )
