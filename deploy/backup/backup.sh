#!/usr/bin/env bash
set -uo pipefail

mkdir -p /backups

snapshot_minio() {
  local destination="$1"
  local before copied after attempt
  before="$(mktemp)"
  copied="$(mktemp)"
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

write_tree_manifest() {
  local source="$1"
  local output="$2"
  if find "$source" -type l -print -quit | grep -q .; then
    echo "Symbolic links are prohibited in backup source: ${source}" >&2
    return 1
  fi
  (
    cd "$source" || exit 1
    find . -mindepth 1 -printf 'entry %y %P\n' | LC_ALL=C sort
    find . -type f -print0 |
      LC_ALL=C sort -z |
      xargs -0 -r sha256sum
  ) >"$output"
}

snapshot_tree() {
  local source="$1"
  local destination="$2"
  local before after attempt
  before="$(mktemp)"
  after="$(mktemp)"

  for attempt in 1 2 3; do
    rm -rf "$destination" || return 1
    mkdir -p "$destination" || return 1
    write_tree_manifest "$source" "$before" || return 1
    cp -a "$source/." "$destination/" || return 1
    write_tree_manifest "$destination" "$copied" || return 1
    write_tree_manifest "$source" "$after" || return 1
    if cmp --silent "$before" "$copied" && cmp --silent "$before" "$after"; then
      cp "$before" "$destination/.researchos-tree-manifest.txt" || return 1
      rm -f "$before" "$copied" "$after"
      return 0
    fi
    echo "Filesystem changed during snapshot attempt ${attempt}: ${source}" >&2
  done
  rm -f "$before" "$copied" "$after"
  echo "Filesystem did not reach a stable snapshot after 3 attempts: ${source}" >&2
  return 1
}

archive_tree() {
  local source="$1"
  local destination="$2"
  local archive="$3"
  snapshot_tree "$source" "$destination" || return 1
  tar -czf "${archive}.partial" -C "$destination" . || return 1
  mv "${archive}.partial" "$archive" || return 1
  verify_archive "$archive"
}

run_backup() {
  local stamp="$1"
  local work database minio knowledge architecture configuration migration manifest
  local database_hash minio_hash knowledge_hash architecture_hash
  local configuration_hash migration_hash manifest_hash backup_set_id
  work="/backups/.work-${stamp}"
  database="/backups/researchos-${stamp}.dump"
  minio="/backups/minio-${stamp}.tar.gz"
  knowledge="/backups/knowledge-${stamp}.tar.gz"
  architecture="/backups/architecture-${stamp}.tar.gz"
  configuration="/backups/configuration-${stamp}.tar.gz"
  migration="/backups/migration-${stamp}.tar.gz"
  manifest="/backups/backup-set-${stamp}.json"
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

  archive_tree /source/knowledge "$work/knowledge" "$knowledge" || return 1
  archive_tree /source/architecture "$work/architecture" "$architecture" || return 1
  archive_tree /source/configuration "$work/configuration" "$configuration" || return 1
  archive_tree /source/migration "$work/migration" "$migration" || return 1

  database_hash="$(cut -d' ' -f1 "${database}.sha256")" || return 1
  minio_hash="$(cut -d' ' -f1 "${minio}.sha256")" || return 1
  knowledge_hash="$(cut -d' ' -f1 "${knowledge}.sha256")" || return 1
  architecture_hash="$(cut -d' ' -f1 "${architecture}.sha256")" || return 1
  configuration_hash="$(cut -d' ' -f1 "${configuration}.sha256")" || return 1
  migration_hash="$(cut -d' ' -f1 "${migration}.sha256")" || return 1
  printf '%s\n' \
    '{' \
    '  "schema_version": "1.0",' \
    "  \"backup_stamp\": \"${stamp}\"," \
    '  "components": [' \
    "    {\"name\":\"architecture\",\"file\":\"$(basename "$architecture")\",\"sha256\":\"${architecture_hash}\"}," \
    "    {\"name\":\"configuration\",\"file\":\"$(basename "$configuration")\",\"sha256\":\"${configuration_hash}\"}," \
    "    {\"name\":\"knowledge\",\"file\":\"$(basename "$knowledge")\",\"sha256\":\"${knowledge_hash}\"}," \
    "    {\"name\":\"migration\",\"file\":\"$(basename "$migration")\",\"sha256\":\"${migration_hash}\"}," \
    "    {\"name\":\"minio\",\"file\":\"$(basename "$minio")\",\"sha256\":\"${minio_hash}\"}," \
    "    {\"name\":\"postgresql\",\"file\":\"$(basename "$database")\",\"sha256\":\"${database_hash}\"}" \
    '  ]' \
    '}' >"${manifest}.partial" || return 1
  mv "${manifest}.partial" "$manifest" || return 1
  sha256sum "$manifest" >"${manifest}.sha256" || return 1
  sha256sum --check "${manifest}.sha256" >/dev/null || return 1
  manifest_hash="$(cut -d' ' -f1 "${manifest}.sha256")" || return 1
  backup_set_id="backup-set:${stamp}:${manifest_hash:0:16}"

  rm -rf "$work" || return 1
  psql -v ON_ERROR_STOP=1 -c "UPDATE backup_runs SET status='completed',database_path='$database',minio_path='$minio',knowledge_path='$knowledge',database_verified=true,minio_verified=true,knowledge_verified=true,backup_set_id='$backup_set_id',backup_set_hash='$manifest_hash',manifest_path='$manifest',integrity_verified=true,completed_at=now(),error=NULL WHERE backup_stamp='$stamp'"
}

while true; do
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  psql -v ON_ERROR_STOP=1 -c "INSERT INTO backup_runs(backup_stamp,status) VALUES ('$stamp','running') ON CONFLICT(backup_stamp) DO NOTHING"
  if ! run_backup "$stamp"; then
    psql -v ON_ERROR_STOP=1 -c "UPDATE backup_runs SET status='failed',error='Backup command failed; inspect service logs',completed_at=now() WHERE backup_stamp='$stamp'"
    rm -rf "/backups/.work-${stamp}"
    rm -f /backups/*-"${stamp}".*.partial
    rm -f \
      "/backups/researchos-${stamp}.dump" \
      "/backups/researchos-${stamp}.dump.sha256" \
      "/backups/minio-${stamp}.tar.gz" \
      "/backups/minio-${stamp}.tar.gz.sha256" \
      "/backups/knowledge-${stamp}.tar.gz" \
      "/backups/knowledge-${stamp}.tar.gz.sha256" \
      "/backups/architecture-${stamp}.tar.gz" \
      "/backups/architecture-${stamp}.tar.gz.sha256" \
      "/backups/configuration-${stamp}.tar.gz" \
      "/backups/configuration-${stamp}.tar.gz.sha256" \
      "/backups/migration-${stamp}.tar.gz" \
      "/backups/migration-${stamp}.tar.gz.sha256" \
      "/backups/backup-set-${stamp}.json" \
      "/backups/backup-set-${stamp}.json.sha256"
  fi
  find /backups -type f \( -name 'researchos-*.dump' -o -name 'researchos-*.dump.sha256' -o -name 'minio-*.tar.gz' -o -name 'minio-*.tar.gz.sha256' -o -name 'knowledge-*.tar.gz' -o -name 'knowledge-*.tar.gz.sha256' -o -name 'architecture-*.tar.gz' -o -name 'architecture-*.tar.gz.sha256' -o -name 'configuration-*.tar.gz' -o -name 'configuration-*.tar.gz.sha256' -o -name 'migration-*.tar.gz' -o -name 'migration-*.tar.gz.sha256' -o -name 'backup-set-*.json' -o -name 'backup-set-*.json.sha256' \) -mtime "+${BACKUP_RETENTION_DAYS}" -delete
  if [[ "${BACKUP_RUN_ONCE:-false}" == "true" ]]; then
    break
  fi
  sleep "$BACKUP_INTERVAL_SECONDS"
done
