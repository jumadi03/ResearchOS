"""Read-only projection of checksum-attested storage tiers."""

from datetime import datetime, timezone
from typing import Any

import psycopg


def read_storage_tier_status(database_url: str) -> dict[str, Any]:
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT component_name, storage_tier, backup_stamp, content_sha256,
                   canonical_locator, verified_at, retention_until
            FROM storage_tier_current
            ORDER BY component_name, storage_tier
            """
        )
        rows = cursor.fetchall()

    items = [
        {
            "component": row[0],
            "tier": row[1],
            "backup_stamp": row[2],
            "content_sha256": row[3],
            "locator": row[4],
            "verified_at": row[5].isoformat(),
            "retention_until": row[6].isoformat() if row[6] else None,
        }
        for row in rows
    ]
    return {
        "schema_version": "1.0",
        "status": "attested" if items else "unavailable",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "items": items,
        "counts": {
            "hot": sum(item["tier"] == "hot" for item in items),
            "archived_local": sum(item["tier"] == "archived_local" for item in items),
            "restore_required": sum(item["tier"] == "restore_required" for item in items),
        },
        "eviction_authorized": False,
    }
