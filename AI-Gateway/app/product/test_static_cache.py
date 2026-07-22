from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.product.static_cache import LocalWorkspaceStaticFiles


def test_local_workspace_assets_are_never_served_stale(tmp_path) -> None:
    (tmp_path / "workspace.js").write_text("const revision = 'current';")
    app = FastAPI()
    app.mount(
        "/workspace-assets",
        LocalWorkspaceStaticFiles(directory=tmp_path),
        name="workspace-assets",
    )

    response = TestClient(app).get("/workspace-assets/workspace.js")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store, max-age=0"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["expires"] == "0"
