"""Create a verified PDF and enqueue an end-to-end parse_document health job."""

from io import BytesIO
import json
import os
from pathlib import Path

import psycopg
from reportlab.pdfgen import canvas

from app.knowledge.ingestion.models import (
    AcquisitionResult, AcquisitionStatus,
)
from app.knowledge.ingestion.registry import DocumentRegistry


output = BytesIO()
pdf = canvas.Canvas(output)
pdf.drawString(40, 800, "Results")
pdf.drawString(40, 780, "The background parser health check succeeded.")
pdf.save()
content = output.getvalue()

root = Path(os.environ["KNOWLEDGE_OUTPUT_ROOT"])
result = AcquisitionResult(
    "worker-health-record", AcquisitionStatus.ACQUIRED, "health-check",
    "https://example.test/worker-health.pdf", "health-check", "health-source",
    "internal-test", "application/pdf", __import__("hashlib").sha256(content).hexdigest(),
    len(content), None, content,
    final_url="https://example.test/worker-health.pdf", http_status=200,
    declared_content_length=len(content), retrieval_method="https_pdf",
    source_definition_id="source-healthcheck",
    query_family_id="query-family-healthcheck",
)
document, _ = DocumentRegistry(root / "documents").register(result)
with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as connection:
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO background_jobs(job_type,payload) VALUES ('parse_document', %s)",
            (json.dumps({"document_id": document.document_id, "created_at": "health-check"}),),
        )
print(document.document_id)
