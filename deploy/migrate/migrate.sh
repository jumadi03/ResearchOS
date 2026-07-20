#!/usr/bin/env bash
set -euo pipefail

psql_base=(psql -v ON_ERROR_STOP=1 -X)

checksum_compatibility_admitted() {
  local signature="$1:$2:$3"
  case "$signature" in
    "29:08fb62ef6c92a9d539a80ff8fe4d7d33d9487212b16ac856b2ed7a220192e53f:8b9e19e7049f1ad08fb403ec08603c94c1fb262100ead136ff97690aa45bbc3e"|\
    "30:ab136fe9a8be8423d38dec53c6848c1f95aff727adde3cbac518023b77e90c71:830baeaeaaf038cc8b118fd6da2f2ffbf2bafc2e1aaaa13918bf9de2aca11317"|\
    "31:4226043650bcd66e1d8a53ac5b76098da0576e6ab3771196587db3f317b5a345:6b1fc28149965aa8c097c6b4f2ff5e6c79c737b6d7a711031486943383d0db87"|\
    "32:6f5d8c46ab624a61a661cd58368031a6960cf83c00b16e83574743677185c0b8:4093679327cb5fd1d8986c03239df2628e5b7f57a561062d9d5103118089a17b")
      return 0 ;;
    *) return 1 ;;
  esac
}

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
        checksum="$(tr -d '\r' < "$file" | sha256sum | cut -d' ' -f1)"
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
  checksum="$(tr -d '\r' < "$file" | sha256sum | cut -d' ' -f1)"
  recorded="$("${psql_base[@]}" -Atc \
    "SELECT checksum_sha256 FROM schema_migrations WHERE version=$version")"
  if [[ -n "$recorded" ]]; then
    if [[ "$recorded" != "$checksum" ]]; then
      if checksum_compatibility_admitted "$version" "$recorded" "$checksum"; then
        echo "Migration checksum compatibility admitted: $filename" >&2
      else
        echo "Migration checksum mismatch: $filename" >&2
        exit 1
      fi
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
