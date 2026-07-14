from dataclasses import dataclass
from typing import Tuple, Type


@dataclass(frozen=True)
class RetryConfig:
    """
    Immutable retry configuration.

    max_attempts:
        Total execution attempts including the first call.

    retryable_exceptions:
        Exception types that are allowed to trigger retry.

    backoff_seconds:
        Fixed delay between attempts.
        Exponential backoff can be introduced later
        without changing the public contract.
    """

    max_attempts: int = 3

    retryable_exceptions: Tuple[Type[Exception], ...] = (
        TimeoutError,
        ConnectionError,
    )

    backoff_seconds: float = 0.5