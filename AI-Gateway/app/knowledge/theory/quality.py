"""Reproducible candidate benchmark and reviewer-outcome summaries."""

import json
from pathlib import Path

from app.knowledge.theory.builder import TheoryBuilder


class AlignmentQualityEvaluator:
    benchmark_path = Path(__file__).with_name("alignment_benchmark_v1.json")

    def benchmark(self, *, threshold: float) -> dict:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be between 0 and 1")
        dataset = json.loads(self.benchmark_path.read_text(encoding="utf-8"))
        results = []
        for case in dataset["cases"]:
            signals = TheoryBuilder.candidate_signals(case["left"], case["right"])
            predicted = (
                len(signals["shared_terms"]) >= 2
                and signals["polarity_match"]
                and signals["score"] >= threshold
            )
            expected = case["expected_outcome"] == "aligned"
            results.append({
                "case_id": case["case_id"], "expected_candidate": expected,
                "predicted_candidate": predicted, "score": signals["score"],
                "shared_terms": signals["shared_terms"],
                "polarity_match": signals["polarity_match"],
            })
        true_positive = sum(
            item["expected_candidate"] and item["predicted_candidate"] for item in results
        )
        false_positive = sum(
            not item["expected_candidate"] and item["predicted_candidate"] for item in results
        )
        true_negative = sum(
            not item["expected_candidate"] and not item["predicted_candidate"] for item in results
        )
        false_negative = sum(
            item["expected_candidate"] and not item["predicted_candidate"] for item in results
        )
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
        return {
            "benchmark_id": dataset["benchmark_id"], "version": dataset["version"],
            "method": dataset["method"], "threshold": threshold,
            "metrics": {
                "true_positive": true_positive, "false_positive": false_positive,
                "true_negative": true_negative, "false_negative": false_negative,
                "precision": round(precision, 4), "recall": round(recall, 4),
            },
            "cases": tuple(results),
        }
