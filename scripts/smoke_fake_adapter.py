"""Smoke test running an end-to-end benchmark with FakeAdapter.

Validates that data loading, profiling, engine execution, central evaluation,
and recommendation scoring succeed without relying on external AutoML venvs.
"""

from __future__ import annotations

import sys
from unittest.mock import patch

import numpy as np
import pandas as pd

from acbs.automl.contracts import RunResult, TrainSpec
from acbs.benchmark.engine import run_benchmark
from acbs.data.loader import _from_frame
from acbs.recommend.scoring import UserPreferences, score_models


class FakeAdapter:
    """Mock runner that simulates a fast, compliant AutoML framework worker."""

    @staticmethod
    def run(spec: TrainSpec, **kwargs) -> RunResult:
        n_test = len(spec.X_test)
        n_classes = spec.n_classes
        # Return uniform or balanced mock probabilities
        if n_classes == 2:
            proba = [[0.2, 0.8] for _ in range(n_test)]
        else:
            proba = [[1.0 / n_classes] * n_classes for _ in range(n_test)]

        return RunResult(
            framework_id=spec.framework_id,
            status="ok",
            proba=proba,
            fit_time_s=0.25,
            predict_time_s=0.015,
            framework_version="fake-1.0.0",
            best_pipeline="FakeEnsembleClassifier(estimators=3)",
            error=None,
        )


def run_smoke() -> None:
    print("[SmokeTest] Preparing synthetic dataset (60 rows, 4 features, binary target)...")
    np.random.seed(42)
    df = pd.DataFrame(
        {
            "num_feat": np.random.randn(60),
            "cat_feat": ["A", "B", "C"] * 20,
            "val_feat": np.linspace(1, 100, 60),
            "target": [0, 1] * 30,
        }
    )
    dataset = _from_frame(df, "target", {"name": "smoke_dataset"})

    cfg = {
        "models": ["logistic_regression"],
        "automl_frameworks": ["fake_automl"],
        "cv_folds": 2,
        "tuning": "none",
        "seed": 42,
    }

    print("[SmokeTest] Running benchmark with FakeAdapter...")
    with patch("acbs.benchmark.engine.run_framework", side_effect=FakeAdapter.run):
        result = run_benchmark(dataset, cfg)

    assert result is not None, "BenchmarkResult is None"
    assert len(result.models) == 2, f"Expected 2 models, got {len(result.models)}"

    model_statuses = {m.model_name: m.status for m in result.models}
    print(f"[SmokeTest] Benchmark completed with models: {model_statuses}")
    assert model_statuses.get("logistic_regression") == "ok", "Logistic Regression failed"
    assert model_statuses.get("fake_automl") == "ok", "FakeAutoML adapter failed"

    from acbs.benchmark.aggregate import results_to_dataframe

    df_res = results_to_dataframe(result)
    prefs = UserPreferences()
    scored = score_models(df_res, prefs)
    assert not scored.empty, "Scoring produced empty results"
    winner = scored.sort_values("rank").iloc[0]["model_name"]
    print(f"[SmokeTest] Multi-criteria evaluation passed. Winner: {winner}")
    print("[SmokeTest] PASS: All smoke assertions verified successfully.")


if __name__ == "__main__":
    try:
        run_smoke()
    except Exception as exc:
        print(f"[SmokeTest] ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

