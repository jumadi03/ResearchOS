#!/usr/bin/env bash
set -uo pipefail

mkdir -p /backups

snapshot_minio() {
  local destination="$1"
  local before after attempt
  before="$(mktemp)"
  after="$(mktemp)"

  mc alias set source "$MINIO_ENDPOINT" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" --api S3v4 >/dev/null || return 1
  for attempt in 1 2 3; do
    rm -rf "$destination" || return 1
    mkdir -p "$destination" || return 1
    mc stat --recursive --json "source/${MINIO_DOCUMENT_BUCKET}" | LC_ALL=C sort >"$before" || return 1
    mc mirror --overwrite --remove --retry \
      "source/${MINIO_DOCUMENT_BUCKET}" "$destination" || return 1
    mc stat --recursive --json "source/${MINIO_DOCUMENT_BUCKET}" | LC_ALL=C sort >"$after" || return 1
    if cmp --silent "$before" "$after"; then
      cp "$before" "$destination/.researchos-object-manifest.jsonl" || return 1
      rm -f "$before" "$after"
      return 0
    fi
    echo "MinIO changed during snapshot attempt ${attempt}; retrying" >&2
  done
  rm -f "$before" "$after"
  echo "MinIO did not reach a stable snapshot after 3 attempts" >&2
  return 1
}

verify_archive() {
  local archive="$1"
  tar -tzf "$archive" >/dev/null || return 1
  sha256sum "$archive" >"${archive}.sha256" || return 1
  sha256sum --check "${archive}.sha256" >/dev/null || return 1
}

run_backup() {
  local stamp="$1"
  local work database minio knowledge
  work="/backups/.work-${stamp}"
  database="/backups/researchos-${stamp}.dump"
  minio="/backups/minio-${stamp}.tar.gz"
  knowledge="/backups/knowledge-${stamp}.tar.gz"
  rm -rf "$work" || return 1
  mkdir -p "$work" || return 1

  pg_dump --format=custom --file="${database}.partial" || return 1
  pg_restore --list "${database}.partial" >/dev/null || return 1
  mv "${database}.partial" "$database" || return 1
  sha256sum "$database" >"${database}.sha256" || return 1
  sha256sum --check "${database}.sha256" >/dev/null || return 1

  snapshot_minio "$work/minio" || return 1
  tar -czf "${minio}.partial" -C "$work/minio" . || return 1
  mv "${minio}.partial" "$minio" || return 1
  verify_archive "$minio" || return 1

  tar -czf "${knowledge}.partial" -C /source/knowledge . || return 1
  mv "${knowledge}.partial" "$knowledge" || return 1
  verify_archive "$knowledge" || return 1

  rm -rf "$work" || return 1
  psql -v ON_ERROR_STOP=1 -c "UPDATE backup_runs SET status='completed',database_path='$database',minio_path='$minio',knowledge_path='$knowledge',database_verified=true,minio_verified=true,knowledge_verified=true,completed_at=now(),error=NULL WHERE backup_stamp='$stamp'"
}

while true; do
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  psql -v ON_ERROR_STOP=1 -c "INSERT INTO backup_runs(backup_stamp,status) VALUES ('$stamp','running') ON CONFLICT(backup_stamp) DO NOTHING"
  if ! run_backup "$stamp"; then
    psql -v ON_ERROR_STOP=1 -c "UPDATE backup_runs SET status='failed',error='Backup command failed; inspect service logs',completed_at=now() WHERE backup_stamp='$stamp'"
    rm -rf "/backups/.work-${stamp}"
    rm -f /backups/*-"${stamp}".*.partial
  fi
  find /backups -type f \( -name 'researchos-*.dump' -o -name 'researchos-*.dump.sha256' -o -name 'minio-*.tar.gz' -o -name 'minio-*.tar.gz.sha256' -o -name 'knowledge-*.tar.gz' -o -name 'knowledge-*.tar.gz.sha256' \) -mtime "+${BACKUP_RETENTION_DAYS}" -delete
  if [[ "${BACKUP_RUN_ONCE:-false}" == "true" ]]; then
    break
  fi
  sleep "$BACKUP_INTERVAL_SECONDS"
done
