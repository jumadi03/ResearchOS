"""Browser entry point for the object-centric ResearchOS workspace."""

import hashlib
from pathlib import Path
import re

from fastapi import APIRouter
from fastapi.responses import HTMLResponse


router = APIRouter(tags=["product-workspace"])
STATIC_ROOT = Path(__file__).resolve().parents[1] / "product" / "static"
INDEX = STATIC_ROOT / "index.html"


def workspace_asset_revision() -> str:
    digest = hashlib.sha256()
    for path in sorted((*STATIC_ROOT.glob("*.css"), *STATIC_ROOT.glob("*.js"))):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def rendered_index() -> str:
    revision = workspace_asset_revision()
    return re.sub(
        r'(/workspace-assets/[^"?]+\.(?:css|js))"',
        rf'\1?v={revision}"',
        INDEX.read_text(encoding="utf-8"),
    )


@router.get("/workspace", include_in_schema=False)
def workspace() -> HTMLResponse:
    return HTMLResponse(
        rendered_index(),
        headers={
            "Cache-Control": "no-store",
            "Clear-Site-Data": '"cache"',
        },
    )
