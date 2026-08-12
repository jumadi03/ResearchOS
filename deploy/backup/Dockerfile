FROM minio/mc:RELEASE.2025-05-21T01-59-54Z AS minio_client

FROM postgres:18-bookworm
COPY --from=minio_client /usr/bin/mc /usr/local/bin/mc
COPY backup.sh /usr/local/bin/backup.sh
RUN chmod 0555 /usr/local/bin/backup.sh /usr/local/bin/mc

ENTRYPOINT ["bash", "/usr/local/bin/backup.sh"]
