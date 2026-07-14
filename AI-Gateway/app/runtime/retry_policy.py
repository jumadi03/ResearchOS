"""
Retry Policy

Menentukan apakah suatu exception layak dilakukan retry.

Pada Sprint-001I Tahap 2B implementasi masih mempertahankan
perilaku lama sehingga seluruh Exception dianggap retryable.
Hal ini menjaga backward compatibility sekaligus memisahkan
keputusan retry dari RetryExecutor.
"""

from typing import Iterable, Tuple, Type


class RetryPolicy:
    """
    Menentukan apakah exception memenuhi syarat retry.
    """

    def __init__(
        self,
        retryable_exceptions: Iterable[Type[BaseException]] | None = None,
    ) -> None:

        if retryable_exceptions is None:
            retryable_exceptions = (
                Exception,
            )

        self._retryable_exceptions: Tuple[Type[BaseException], ...] = tuple(
            retryable_exceptions
        )

    def should_retry(self, exception: BaseException) -> bool:
        """
        Mengembalikan True apabila exception boleh di-retry.
        """
        return isinstance(
            exception,
            self._retryable_exceptions,
        )