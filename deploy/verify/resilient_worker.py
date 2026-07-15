"""End-to-end verification for lease recovery, retry, and dead-letter behavior."""

from __future__ import annotations

import os
from time import monotonic, sleep

import psycopg


DATABASE_URL = os.environ["DATABASE_URL"]


def main() -> None:
    with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO background_jobs(
                    job_type,payload,status,attempts,locked_by,lease_expires_at
                ) VALUES (
                    'normalize_metadata',
                    '{"record_id":"lease-recovery-health","metadata":{"Title":"Recovered"},"source_hash":"lease-v1"}',
                    'running',0,'expired-worker',now() - interval '1 minute'
                ) RETURNING job_id
            """)
            recovered_job = cursor.fetchone()[0]
            cursor.execute("""
                INSERT INTO background_jobs(job_type,payload)
                VALUES ('parse_document','{}') RETURNING job_id
            """)
            dead_letter_job = cursor.fetchone()[0]

        deadline = monotonic() + 60
        states = {}
        while monotonic() < deadline:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT job_id,status,attempts,locked_by,lease_expires_at,error
                    FROM background_jobs WHERE job_id=ANY(%s)
                """, ([recovered_job, dead_letter_job],))
                states = {row[0]: row[1:] for row in cursor.fetchall()}
            if (
                states.get(recovered_job, (None,))[0] == "complete"
                and states.get(dead_letter_job, (None,))[0] == "dead_letter"
            ):
                break
            sleep(1)
        else:
            raise AssertionError(f"Worker lifecycle did not converge: {states}")

        recovered = states[recovered_job]
        dead_letter = states[dead_letter_job]
        assert recovered[0] == "complete" and recovered[1] == 1
        assert recovered[2] is None and recovered[3] is None
        assert dead_letter[0] == "dead_letter" and dead_letter[1] == 3
        assert dead_letter[2] is None and dead_letter[3] is None
        assert "parse_document requires document_id" in dead_letter[4]

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT metadata->>'title',source_hash FROM normalized_metadata
                WHERE record_id='lease-recovery-health'
            """)
            assert cursor.fetchone() == ("Recovered", "lease-v1")

    print("resilient-worker=passed")


if __name__ == "__main__":
    main()
