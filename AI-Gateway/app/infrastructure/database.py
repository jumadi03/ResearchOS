"""Database schema compatibility checks for application startup."""


def require_schema_version(database_url: str, expected_version: int) -> None:
    import psycopg

    try:
        with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
            cursor.execute("SELECT COALESCE(max(version),0) FROM schema_migrations")
            actual_version = cursor.fetchone()[0]
    except psycopg.Error as exc:
        raise RuntimeError("Database schema migration ledger is unavailable") from exc
    if actual_version != expected_version:
        raise RuntimeError(
            f"Database schema version {actual_version} does not match required version "
            f"{expected_version}"
        )
