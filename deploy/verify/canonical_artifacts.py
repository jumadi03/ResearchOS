"""DATA-002H canonical artifact and lifecycle acceptance check."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os

from app.knowledge.repositories.postgres import PostgresScientificDataRepository


def iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def main() -> None:
    repository = PostgresScientificDataRepository(os.environ["DATABASE_URL"])
    now = datetime.now(timezone.utc)
    suffix = now.strftime("%Y%m%dT%H%M%S%f")
    project_id = f"artifact-healthcheck-{suffix}"
    artifacts = (
        (f"theory-{suffix}", "theory_bundle", "Theory healthcheck", "draft"),
        (f"gap-{suffix}", "gap_analysis", "Gap healthcheck", "draft"),
        (f"validation-{suffix}", "validation_report", "Validation healthcheck", "validated"),
        (f"publication-{suffix}", "publication_package", "Publication healthcheck", "published"),
    )
    created = {}
    for artifact_id, artifact_type, title, status in artifacts:
        values = dict(
            artifact_id=artifact_id, project_id=project_id,
            artifact_type=artifact_type, title=title, status=status,
            metadata={"healthcheck": True, "artifact_type": artifact_type},
            actor_id="researcher@researchos.local", occurred_at=iso(now),
        )
        event = repository.persist_artifact(**values)
        assert repository.persist_artifact(**values).lifecycle_event_id == event.lifecycle_event_id
        created[artifact_id] = event

    theory_id = artifacts[0][0]
    review_values = dict(
        to_status="review", actor_id="reviewer@researchos.local",
        rationale="Ready for formal assessment.", occurred_at=iso(now + timedelta(seconds=1)),
    )
    review = repository.transition_artifact(theory_id, **review_values)
    assert repository.transition_artifact(theory_id, **review_values).lifecycle_event_id == review.lifecycle_event_id
    validated = repository.transition_artifact(
        theory_id, to_status="validated", actor_id="reviewer@researchos.local",
        rationale="Scientific review completed.", occurred_at=iso(now + timedelta(seconds=2)),
    )
    assert validated.from_status == "review"
    try:
        repository.transition_artifact(
            artifacts[1][0], to_status="published", actor_id="reviewer@researchos.local",
            rationale="Invalid lifecycle jump test.", occurred_at=iso(now + timedelta(seconds=3)),
        )
    except ValueError as exc:
        assert "Invalid artifact transition" in str(exc)
    else:
        raise AssertionError("Artifact lifecycle jump was not rejected")

    with repository._connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT r.artifact_type,r.status,c.lifecycle_status,c.current_version,
                       count(l.lifecycle_event_id)
                FROM research_artifacts r
                JOIN canonical_objects c ON c.object_id=r.artifact_id
                JOIN artifact_lifecycle_events l ON l.artifact_id=r.artifact_id
                WHERE r.project_id=%s
                GROUP BY r.artifact_type,r.status,c.lifecycle_status,c.current_version
                ORDER BY r.artifact_type
            """, (project_id,))
            rows = cursor.fetchall()
    assert len(rows) == 4, rows
    states = {row[0]: row[1:] for row in rows}
    assert states["theory_bundle"] == ("validated", "validated", 3, 3)
    assert states["gap_analysis"] == ("draft", "draft", 1, 1)
    assert states["validation_report"] == ("validated", "validated", 1, 1)
    assert states["publication_package"] == ("published", "published", 1, 1)

    try:
        with repository._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM artifact_lifecycle_events WHERE lifecycle_event_id=%s",
                    (review.lifecycle_event_id,),
                )
    except Exception as exc:
        assert "append-only" in str(exc)
    else:
        raise AssertionError("Artifact lifecycle mutation was not rejected")
    print("canonical artifact healthcheck: passed")


if __name__ == "__main__":
    main()
