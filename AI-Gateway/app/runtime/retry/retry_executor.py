import time
from typing import Callable, TypeVar

from .retry_policy import RetryPolicy

T = TypeVar("T")


class RetryExecutor:
    """
    Executes an operation using the configured RetryPolicy.

    Mendukung:
    - execute() : normal request
    - stream()  : streaming request
    """

    def __init__(self, policy: RetryPolicy):
        self._policy = policy

    def execute(
        self,
        operation: Callable[[], T],
    ) -> T:

        attempt = 1

        while True:

            try:
                return operation()

            except Exception as exc:

                if not self._policy.should_retry(
                    exc,
                    attempt,
                ):
                    raise

                time.sleep(
                    self._policy.get_backoff(
                        attempt
                    )
                )

                attempt += 1

    def stream(
        self,
        operation,
    ):

        attempt = 1

        while True:

            try:

                yield from operation()
                return

            except Exception as exc:

                if not self._policy.should_retry(
                    exc,
                    attempt,
                ):
                    raise

                time.sleep(
                    self._policy.get_backoff(
                        attempt
                    )
                )

                attempt += 1