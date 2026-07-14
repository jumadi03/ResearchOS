from .metrics_collector import MetricsCollector


collector = MetricsCollector()


def record(canonical_response: dict) -> None:
    collector.collect(canonical_response)