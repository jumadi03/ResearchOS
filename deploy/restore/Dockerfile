FROM minio/mc:RELEASE.2025-05-21T01-59-54Z AS minio_client

FROM postgres:17-bookworm
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip \
    && pip3 install --break-system-packages --no-cache-dir cryptography==49.0.0 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=minio_client /usr/bin/mc /usr/local/bin/mc
COPY deploy/verify/recovery_coverage.py /opt/researchos/recovery_coverage.py
COPY deploy/restore/restore_drill.py /opt/researchos/restore_drill.py
COPY AI-Gateway/app/product/restore_attestation.py /opt/researchos/restore_attestation.py
RUN chmod 0555 /usr/local/bin/mc /opt/researchos/restore_drill.py
WORKDIR /opt/researchos
ENTRYPOINT ["python3", "/opt/researchos/restore_drill.py"]
