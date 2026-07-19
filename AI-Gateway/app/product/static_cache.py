"""Cache policy for the locally served ResearchOS workspace assets."""

from starlette.responses import Response
from starlette.staticfiles import StaticFiles


class LocalWorkspaceStaticFiles(StaticFiles):
    """Serve local UI assets without retaining stale container revisions."""

    async def get_response(self, path: str, scope: dict) -> Response:
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
