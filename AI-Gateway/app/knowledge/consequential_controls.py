"""PostgreSQL control plane for SGF-020C consequential research."""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any


class ConsequentialResearchControls:
    def __init__(self, database_url: str):
        if not database_url:
            raise ValueError("DATABASE_URL is required")
        self.database_url = database_url

    def _connect(self):
        import psycopg

        return psycopg.connect(self.database_url)

    @staticmethod
    def _row(cursor) -> dict[str, Any]:
        names = [item.name for item in cursor.description]
        return dict(zip(names, cursor.fetchone(), strict=True))

    @staticmethod
    def _authority(cursor, actor_id: str) -> str:
        cursor.execute(
            """
            SELECT authority_id::text FROM human_authorities
            WHERE stable_subject_id=%s AND authority_status='active'
            """,
            (actor_id,),
        )
        row = cursor.fetchone()
        if row is None:
            raise PermissionError(
                "Authenticated principal is not a registered active human authority"
            )
        return row[0]

    @staticmethod
    def _provenance(
        cursor, actor_id: str, event_type: str, payload: dict[str, Any],
        occurred_at: str,
    ) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        event_hash = sha256(
            f"{actor_id}:{event_type}:{occurred_at}:{canonical}".encode("utf-8")
        ).hexdigest()
        cursor.execute(
            """
            INSERT INTO provenance_events(
                execution_id,agent_id,event_type,event_payload,
                occurred_at,event_hash
            ) VALUES ('sgf020c-control-plane',%s,%s,%s,%s,%s)
            RETURNING provenance_id::text
            """,
            (actor_id, event_type, canonical, occurred_at, event_hash),
        )
        return cursor.fetchone()[0]

    def list_profiles(self) -> list[dict[str, Any]]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT profile_id::text,profile_key,version,name,risk_class,
                       jurisdiction,required_reviewer_quorum,
                       required_qualification_kind,require_unanimous_review,
                       require_ethics_reference,
                       require_distinct_release_authority,
                       decision_validity_days,policy_document_id,
                       policy_document_hash,effective_from,retired_at
                FROM consequential_research_profiles
                ORDER BY profile_key,version
                """
            )
            names = [item.name for item in cursor.description]
            return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]

    def create_profile(self, values: dict[str, Any], actor_id: str) -> dict[str, Any]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO consequential_research_profiles(
                    profile_key,version,name,risk_class,jurisdiction,
                    required_reviewer_quorum,required_qualification_kind,
                    require_unanimous_review,require_ethics_reference,
                    require_distinct_release_authority,decision_validity_days,
                    policy_document_id,policy_document_hash,effective_from,created_by
                ) VALUES (
                    %(profile_key)s,%(version)s,%(name)s,%(risk_class)s,
                    %(jurisdiction)s,%(required_reviewer_quorum)s,
                    %(required_qualification_kind)s,%(require_unanimous_review)s,
                    %(require_ethics_reference)s,
                    %(require_distinct_release_authority)s,
                    %(decision_validity_days)s,%(policy_document_id)s,
                    %(policy_document_hash)s,%(effective_from)s,%(created_by)s
                )
                RETURNING profile_id::text,profile_key,version,name,risk_class,
                          jurisdiction,required_reviewer_quorum,
                          required_qualification_kind,effective_from
                """,
                {**values, "created_by": actor_id},
            )
            result = self._row(cursor)
        return result

    def register_authority(
        self, values: dict[str, Any], actor_id: str
    ) -> dict[str, Any]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO human_authorities(
                    workspace_user_id,stable_subject_id,display_name,
                    identity_verified_at,identity_verified_by
                ) VALUES (
                    %(workspace_user_id)s,%(stable_subject_id)s,%(display_name)s,
                    %(identity_verified_at)s,%(identity_verified_by)s
                )
                RETURNING authority_id::text,workspace_user_id::text,
                          stable_subject_id,display_name,authority_status,
                          identity_verified_at
                """,
                {**values, "identity_verified_by": actor_id},
            )
            result = self._row(cursor)
        return result

    def activate_profile(
        self, project_id: str, profile_id: str, rationale: str,
        activated_at: str, actor_id: str,
    ) -> dict[str, Any]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO project_consequential_profiles(
                    project_id,profile_id,activated_by,activated_at,rationale
                ) VALUES (%s,%s,%s,%s,%s)
                RETURNING assignment_id::text,project_id,profile_id::text,
                          activated_by,activated_at,rationale
                """,
                (project_id, profile_id, actor_id, activated_at, rationale),
            )
            result = self._row(cursor)
        return result

    def add_qualification(
        self, authority_id: str, values: dict[str, Any], actor_id: str
    ) -> dict[str, Any]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO authority_qualifications(
                    authority_id,qualification_kind,issuing_body,jurisdiction,
                    scope,credential_reference,credential_hash,valid_from,
                    valid_until,verified_by,verified_at
                ) VALUES (
                    %(authority_id)s,%(qualification_kind)s,%(issuing_body)s,
                    %(jurisdiction)s,%(scope)s,%(credential_reference)s,
                    %(credential_hash)s,%(valid_from)s,%(valid_until)s,
                    %(verified_by)s,%(verified_at)s
                )
                RETURNING qualification_id::text,authority_id::text,
                          qualification_kind,issuing_body,jurisdiction,
                          valid_from,valid_until,status
                """,
                {
                    **values, "scope": json.dumps(values["scope"]),
                    "authority_id": authority_id, "verified_by": actor_id,
                },
            )
            return self._row(cursor)

    def record_ethics(
        self, values: dict[str, Any], actor_id: str
    ) -> dict[str, Any]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO ethics_approvals(
                    project_id,protocol_identifier,issuing_body,jurisdiction,
                    decision,scope,document_reference,document_hash,valid_from,
                    valid_until,recorded_by,recorded_at,
                    supersedes_ethics_approval_id
                ) VALUES (
                    %(project_id)s,%(protocol_identifier)s,%(issuing_body)s,
                    %(jurisdiction)s,%(decision)s,%(scope)s,
                    %(document_reference)s,%(document_hash)s,%(valid_from)s,
                    %(valid_until)s,%(recorded_by)s,%(recorded_at)s,
                    %(supersedes_ethics_approval_id)s
                )
                RETURNING ethics_approval_id::text,project_id,
                          protocol_identifier,issuing_body,jurisdiction,
                          decision,valid_from,valid_until,status
                """,
                {
                    **values, "scope": json.dumps(values["scope"]),
                    "recorded_by": actor_id,
                },
            )
            return self._row(cursor)

    def open_decision(
        self, values: dict[str, Any], actor_id: str
    ) -> dict[str, Any]:
        ethics_ids = values.pop("ethics_approval_ids", [])
        with self._connect() as connection, connection.cursor() as cursor:
            proposer = self._authority(cursor, actor_id)
            provenance = self._provenance(
                cursor, actor_id, "consequential_decision_opened",
                {
                    "project_id": values["project_id"],
                    "target_id": values["target_id"],
                    "target_content_hash": values["target_content_hash"],
                },
                values["opened_at"],
            )
            cursor.execute(
                """
                INSERT INTO scientific_decisions(
                    project_id,profile_id,decision_type,target_type,target_id,
                    target_version,target_content_hash,proposed_decision,
                    proposer_authority_id,release_authority_id,rationale,
                    policy_snapshot_hash,opened_at,review_due_at,valid_until,
                    provenance_id
                ) VALUES (
                    %(project_id)s,%(profile_id)s,%(decision_type)s,
                    %(target_type)s,%(target_id)s,%(target_version)s,
                    %(target_content_hash)s,%(proposed_decision)s,
                    %(proposer_authority_id)s,%(release_authority_id)s,
                    %(rationale)s,%(policy_snapshot_hash)s,%(opened_at)s,
                    %(review_due_at)s,%(valid_until)s,%(provenance_id)s
                )
                RETURNING decision_id::text,project_id,profile_id::text,
                          decision_type,target_type,target_id,target_version,
                          target_content_hash,proposer_authority_id::text,
                          release_authority_id::text,opened_at,review_due_at,
                          valid_until
                """,
                {
                    **values,
                    "proposer_authority_id": proposer,
                    "provenance_id": provenance,
                },
            )
            result = self._row(cursor)
            for ethics_id in ethics_ids:
                cursor.execute(
                    """
                    INSERT INTO decision_ethics_references(
                        decision_id,ethics_approval_id,linked_by,linked_at
                    ) VALUES (%s,%s,%s,%s)
                    """,
                    (result["decision_id"], ethics_id, actor_id, values["opened_at"]),
                )
            return result

    def declare_conflict(
        self, decision_id: str, values: dict[str, Any], actor_id: str
    ) -> dict[str, Any]:
        with self._connect() as connection, connection.cursor() as cursor:
            authority = self._authority(cursor, actor_id)
            provenance = self._provenance(
                cursor, actor_id, "conflict_of_interest_declared",
                {"decision_id": decision_id, "declaration": values["declaration"]},
                values["declared_at"],
            )
            cursor.execute(
                """
                INSERT INTO conflict_of_interest_declarations(
                    decision_id,authority_id,declaration,details,mitigation,
                    declared_at,provenance_id
                ) VALUES (%s,%s,%s,%s,%s,%s,%s)
                RETURNING declaration_id::text,decision_id::text,
                          authority_id::text,declaration,details,mitigation,
                          declared_at
                """,
                (
                    decision_id, authority, values["declaration"], values["details"],
                    values["mitigation"], values["declared_at"], provenance,
                ),
            )
            return self._row(cursor)

    def vote(
        self, decision_id: str, values: dict[str, Any], actor_id: str
    ) -> dict[str, Any]:
        with self._connect() as connection, connection.cursor() as cursor:
            authority = self._authority(cursor, actor_id)
            provenance = self._provenance(
                cursor, actor_id, "consequential_decision_vote",
                {
                    "decision_id": decision_id,
                    "vote": values["vote"],
                    "reviewed_target_hash": values["reviewed_target_hash"],
                },
                values["occurred_at"],
            )
            cursor.execute(
                """
                INSERT INTO decision_review_votes(
                    decision_id,reviewer_authority_id,vote,rationale,
                    reviewed_target_hash,occurred_at,provenance_id
                ) VALUES (%s,%s,%s,%s,%s,%s,%s)
                RETURNING vote_id::text,decision_id::text,
                          reviewer_authority_id::text,vote,rationale,
                          reviewed_target_hash,occurred_at
                """,
                (
                    decision_id, authority, values["vote"], values["rationale"],
                    values["reviewed_target_hash"], values["occurred_at"], provenance,
                ),
            )
            return self._row(cursor)

    def evaluate_quorum(
        self, decision_id: str, evaluated_at: str, actor_id: str
    ) -> dict[str, Any]:
        readiness = self.readiness(decision_id)
        if readiness is None:
            raise ValueError("Decision not found")
        controls = (
            "ethics_satisfied", "qualifications_satisfied",
            "conflicts_satisfied", "release_authority_satisfied",
            "freshness_satisfied",
        )
        failures = [name for name in controls if not readiness[name]]
        if readiness["approval_count"] < readiness["required_reviewer_quorum"]:
            failures.append("reviewer_quorum")
        if readiness["rejection_count"]:
            failures.append("rejection_present")
        payload = {
            "decision_id": decision_id,
            "evaluated_at": evaluated_at,
            "ready": readiness["ready"],
            "failures": failures,
        }
        result_hash = sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO decision_quorum_results(
                    decision_id,evaluated_at,passed,approval_count,
                    rejection_count,distinct_reviewer_count,ethics_satisfied,
                    qualifications_satisfied,conflicts_satisfied,
                    release_authority_satisfied,freshness_satisfied,
                    failure_reasons,evaluated_by,result_hash
                ) VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                )
                RETURNING quorum_result_id::text,decision_id::text,
                          evaluated_at,passed,approval_count,rejection_count,
                          distinct_reviewer_count,failure_reasons,result_hash
                """,
                (
                    decision_id, evaluated_at, readiness["ready"],
                    readiness["approval_count"], readiness["rejection_count"],
                    readiness["distinct_reviewer_count"],
                    readiness["ethics_satisfied"],
                    readiness["qualifications_satisfied"],
                    readiness["conflicts_satisfied"],
                    readiness["release_authority_satisfied"],
                    readiness["freshness_satisfied"], json.dumps(failures),
                    actor_id, result_hash,
                ),
            )
            return self._row(cursor)

    def file_appeal(
        self, decision_id: str, values: dict[str, Any], actor_id: str
    ) -> dict[str, Any]:
        with self._connect() as connection, connection.cursor() as cursor:
            authority = self._authority(cursor, actor_id)
            provenance = self._provenance(
                cursor, actor_id, "consequential_decision_appealed",
                {"decision_id": decision_id, "grounds": values["grounds"]},
                values["filed_at"],
            )
            cursor.execute(
                """
                INSERT INTO decision_appeals(
                    contested_decision_id,appellant_authority_id,grounds,
                    requested_remedy,supporting_evidence,filed_at,provenance_id
                ) VALUES (%s,%s,%s,%s,%s,%s,%s)
                RETURNING appeal_id::text,contested_decision_id::text,
                          appellant_authority_id::text,grounds,
                          requested_remedy,filed_at
                """,
                (
                    decision_id, authority, values["grounds"],
                    values["requested_remedy"],
                    json.dumps(values["supporting_evidence"]),
                    values["filed_at"], provenance,
                ),
            )
            return self._row(cursor)

    def record_appeal_event(
        self, appeal_id: str, values: dict[str, Any], actor_id: str
    ) -> dict[str, Any]:
        with self._connect() as connection, connection.cursor() as cursor:
            authority = self._authority(cursor, actor_id)
            provenance = self._provenance(
                cursor, actor_id, "consequential_appeal_event",
                {
                    "appeal_id": appeal_id,
                    "event_type": values["event_type"],
                    "resulting_decision_id": values["resulting_decision_id"],
                },
                values["occurred_at"],
            )
            cursor.execute(
                """
                INSERT INTO decision_appeal_events(
                    appeal_id,event_type,actor_authority_id,rationale,
                    resulting_decision_id,occurred_at,provenance_id
                ) VALUES (%s,%s,%s,%s,%s,%s,%s)
                RETURNING appeal_event_id::text,appeal_id::text,event_type,
                          actor_authority_id::text,rationale,
                          resulting_decision_id::text,occurred_at
                """,
                (
                    appeal_id, values["event_type"], authority,
                    values["rationale"], values["resulting_decision_id"],
                    values["occurred_at"], provenance,
                ),
            )
            return self._row(cursor)

    def revalidation_queue(
        self, project_id: str | None = None
    ) -> list[dict[str, Any]]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT decision_id::text,project_id,decision_type,target_type,
                       target_id,review_due_at,valid_until,reason,
                       enforcement_state
                FROM consequential_revalidation_queue
                WHERE (%s::text IS NULL OR project_id=%s)
                ORDER BY
                    CASE enforcement_state WHEN 'blocked' THEN 0 ELSE 1 END,
                    review_due_at,decision_id
                """,
                (project_id, project_id),
            )
            names = [item.name for item in cursor.description]
            return [
                dict(zip(names, row, strict=True)) for row in cursor.fetchall()
            ]

    def readiness(self, decision_id: str) -> dict[str, Any] | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT decision_id::text,project_id,decision_type,target_type,
                       target_id,target_content_hash,required_reviewer_quorum,
                       approval_count,rejection_count,distinct_reviewer_count,
                       qualifications_satisfied,conflicts_satisfied,
                       ethics_satisfied,release_authority_satisfied,
                       freshness_satisfied,ready
                FROM consequential_decision_readiness
                WHERE decision_id=%s
                """,
                (decision_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            names = [item.name for item in cursor.description]
            return dict(zip(names, row, strict=True))

    def record_audit_event(
        self, *, actor_id: str, event_type: str, payload: dict[str, Any]
    ) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        event_hash = sha256(
            f"{actor_id}:{event_type}:{canonical}".encode("utf-8")
        ).hexdigest()
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO provenance_events(
                    execution_id,agent_id,event_type,event_payload,
                    occurred_at,event_hash
                ) VALUES ('sgf020c-control-plane',%s,%s,%s,now(),%s)
                ON CONFLICT(event_hash) DO NOTHING
                RETURNING provenance_id::text
                """,
                (actor_id, event_type, canonical, event_hash),
            )
            row = cursor.fetchone()
        return row[0] if row else event_hash
