"""Browser entry point for the object-centric ResearchOS workspace."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse


router = APIRouter(tags=["product-workspace"])
INDEX = Path(__file__).resolve().parents[1] / "product" / "static" / "index.html"


@router.get("/workspace", include_in_schema=False)
def workspace() -> FileResponse:
    return FileResponse(INDEX)
