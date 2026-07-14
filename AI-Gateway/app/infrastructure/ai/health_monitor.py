class HealthMonitor:
    """
    Memeriksa kesehatan provider AI.

    Versi pertama hanya memanggil method health()
    milik provider. Nantinya dapat dikembangkan
    menjadi health check dengan cache, timeout,
    retry, dan circuit breaker.
    """

    def is_available(self, provider) -> bool:
        return provider.health()