#!/usr/bin/env bash
set -euo pipefail
mkdir -p /backups
while true; do
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  target="/backups/researchos-${stamp}.dump"
  psql -v ON_ERROR_STOP=1 -c "INSERT INTO backup_runs(backup_stamp,status) VALUES ('$stamp','running') ON CONFLICT(backup_stamp) DO NOTHING"
  pg_dump --format=custom --file="$target"
  pg_restore --list "$target" >/dev/null
  tar -czf "/backups/minio-${stamp}.tar.gz" -C /source/minio .
  tar -tzf "/backups/minio-${stamp}.tar.gz" >/dev/null
  tar -czf "/backups/knowledge-${stamp}.tar.gz" -C /source/knowledge .
  tar -tzf "/backups/knowledge-${stamp}.tar.gz" >/dev/null
  psql -v ON_ERROR_STOP=1 -c "UPDATE backup_runs SET status='completed',database_path='$target',minio_path='/backups/minio-${stamp}.tar.gz',knowledge_path='/backups/knowledge-${stamp}.tar.gz',database_verified=true,minio_verified=true,knowledge_verified=true,completed_at=now() WHERE backup_stamp='$stamp'"
  find /backups -type f \( -name 'researchos-*.dump' -o -name 'minio-*.tar.gz' -o -name 'knowledge-*.tar.gz' \) -mtime "+${BACKUP_RETENTION_DAYS}" -delete
  sleep "$BACKUP_INTERVAL_SECONDS"
done
