from app.infrastructure.ai.provider_bootstrap import build_registry
from app.infrastructure.ai.routing_policy import RoutingPolicy
from app.infrastructure.ai.health_monitor import HealthMonitor
from app.infrastructure.ai.response_normalizer import ResponseNormalizer
from app.runtime.execution.runtime_executor import RuntimeExecutor
from app.runtime.models.runtime_request import RuntimeRequest


class AIRouter:
    """
    AI Router hanya bertugas
    mengorkestrasi request.

    Router tidak mengambil keputusan
    mengenai provider.
    """

    def __init__(self):

        self.registry = build_registry()

        self.policy = RoutingPolicy(
            self.registry
        )

        self.health = HealthMonitor()

        self.normalizer = ResponseNormalizer()

        self.runtime = RuntimeExecutor()

    def execute(
        self,
        request: RuntimeRequest,
    ):

        decision = self.policy.select(
            request
        )

        provider_name = decision.provider

        provider = self.registry.get(
            provider_name
        )

        if not self.health.is_available(
            provider
        ):
            raise RuntimeError(
                f"Provider '{provider_name}' is unavailable."
            )

        response = self.runtime.execute(
            provider,
            request,
        )

        return self.normalizer.normalize(
            provider_name,
            response,
        )

    def stream(
        self,
        request: RuntimeRequest,
    ):

        decision = self.policy.select(
            request
        )

        provider_name = decision.provider

        provider = self.registry.get(
            provider_name
        )

        if not self.health.is_available(
            provider
        ):
            raise RuntimeError(
                f"Provider '{provider_name}' is unavailable."
            )

        yield from self.runtime.stream(
            provider,
            request,
        )