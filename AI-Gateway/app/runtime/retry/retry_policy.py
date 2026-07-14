from .retry_config import RetryConfig


class RetryPolicy:
    """
    Determines whether an exception is eligible for retry.
    """

    def __init__(self, config: RetryConfig):
        self._config = config

    @property
    def config(self) -> RetryConfig:
        return self._config

    def should_retry(
        self,
        exception: Exception,
        attempt: int,
    ) -> bool:
        """
        Returns True if execution should be retried.
        """

        if attempt >= self._config.max_attempts:
            return False

        return isinstance(
            exception,
            self._config.retryable_exceptions,
        )
    
    def get_backoff(
        self,
        attempt: int,
    ) -> float:
        """
        Returns the backoff duration before the next retry attempt.

        Currently implements a fixed backoff strategy.
        This method intentionally encapsulates the backoff calculation
        so future strategies (exponential, jitter, adaptive, etc.)
        can be introduced without changing RetryExecutor.
        """

        return self._config.backoff_seconds