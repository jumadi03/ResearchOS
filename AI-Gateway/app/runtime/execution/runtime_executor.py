from app.runtime.models.runtime_request import RuntimeRequest

from app.runtime.retry.retry_config import RetryConfig
from app.runtime.retry.retry_policy import RetryPolicy
from app.runtime.retry.retry_executor import RetryExecutor


class RuntimeExecutor:
    """
    Runtime execution entry point.

    Seluruh eksekusi provider
    harus melewati RuntimeExecutor.

    Mendukung:

    - execute()
    - stream()
    """

    def __init__(self):

        config = RetryConfig()

        policy = RetryPolicy(config)

        self._retry = RetryExecutor(policy)

    def execute(
        self,
        provider,
        request: RuntimeRequest,
    ):

        return self._retry.execute(
            lambda: provider.execute(
                request
            )
        )

    def stream(
        self,
        provider,
        request: RuntimeRequest,
    ):

        return self._retry.stream(
            lambda: provider.stream(
                request
            )
        )
