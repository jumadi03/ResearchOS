from app.runtime.models import RoutingDecision
from app.runtime.models.runtime_request import RuntimeRequest
from app.runtime.routing import RoutingEngine

from app.infrastructure.ai.provider_registry import ProviderRegistry


class RoutingPolicy:
    """
    High-level routing policy.

    Delegates routing execution to
    Runtime RoutingEngine.
    """

    def __init__(
        self,
        registry: ProviderRegistry,
    ):

        self.engine = RoutingEngine(
            registry
        )

    def select(
        self,
        request: RuntimeRequest,
    ) -> RoutingDecision:

        #
        # Sprint-001P
        #
        # RuntimeRequest telah menjadi
        # Canonical Runtime Input Model.
        #
        # RoutingEngine masih menggunakan
        # prompt sebagai kontrak internal.
        #

        return self.engine.route(
            request.prompt
        )