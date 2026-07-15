#!/usr/bin/env bash
set -euo pipefail

psql_base=(psql -v ON_ERROR_STOP=1 -X)

"${psql_base[@]}" <<'SQL'
CREATE TABLE IF NOT EXISTS schema_migrations (
    version integer PRIMARY KEY,
    filename text NOT NULL UNIQUE,
    checksum_sha256 text NOT NULL,
    applied_at timestamptz NOT NULL DEFAULT now(),
    applied_by text NOT NULL
);
SQL

applied_count="$("${psql_base[@]}" -Atc 'SELECT count(*) FROM schema_migrations')"
if [[ "$applied_count" == "0" ]]; then
  canonical_exists="$("${psql_base[@]}" -Atc "SELECT to_regclass('public.canonical_objects') IS NOT NULL")"
  if [[ "$canonical_exists" == "t" ]]; then
    baseline_complete="$("${psql_base[@]}" -Atc "SELECT
      to_regclass('public.storage_contract_registry') IS NOT NULL
      AND to_regclass('public.workspace_users') IS NOT NULL
      AND to_regclass('public.backup_runs') IS NOT NULL
      AND to_regclass('public.ai_analysis_runs') IS NOT NULL")"
    if [[ "$baseline_complete" != "t" ]]; then
      echo "Existing database is not a complete ResearchOS v14 baseline" >&2
      exit 1
    fi
    baseline=14
    lease_exists="$("${psql_base[@]}" -Atc "SELECT EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_schema='public' AND table_name='background_jobs'
        AND column_name='available_at')")"
    if [[ "$lease_exists" == "t" ]]; then baseline=15; fi
    for file in /migrations/*.sql; do
      version="$(basename "$file" | cut -d_ -f1 | sed 's/^0*//')"
      if (( version <= baseline )); then
        checksum="$(sha256sum "$file" | cut -d' ' -f1)"
        filename="$(basename "$file")"
        printf "INSERT INTO schema_migrations(version,filename,checksum_sha256,applied_by) VALUES (%s,'%s','%s','detected-baseline');\n" \
          "$version" "$filename" "$checksum" | "${psql_base[@]}"
      fi
    done
  fi
fi

for file in /migrations/*.sql; do
  filename="$(basename "$file")"
  version="$(printf '%s' "$filename" | cut -d_ -f1 | sed 's/^0*//')"
  checksum="$(sha256sum "$file" | cut -d' ' -f1)"
  recorded="$("${psql_base[@]}" -Atc \
    "SELECT checksum_sha256 FROM schema_migrations WHERE version=$version")"
  if [[ -n "$recorded" ]]; then
    if [[ "$recorded" != "$checksum" ]]; then
      echo "Migration checksum mismatch: $filename" >&2
      exit 1
    fi
    continue
  fi
  {
    printf 'SELECT pg_advisory_xact_lock(20260716);\n'
    cat "$file"
    printf "\nINSERT INTO schema_migrations(version,filename,checksum_sha256,applied_by) VALUES (%s,'%s','%s','migration-runner');\n" "$version" "$filename" "$checksum"
  } | "${psql_base[@]}" --single-transaction
done

"${psql_base[@]}" -Atc \
  "SELECT 'schema-version=' || COALESCE(max(version),0) FROM schema_migrations"
