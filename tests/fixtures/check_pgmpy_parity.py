#!/usr/bin/env python3
"""Optionally compare the independent golden fixture with current pgmpy."""

from __future__ import annotations

import argparse
import importlib
import json
import math
import numbers
import sys
from collections import Counter
from collections.abc import Callable, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any


DEFAULT_GOLDEN = Path(__file__).with_name("golden.json")
DEFAULT_TOLERANCE = 1e-7
# pgmpy's Pillai statistic and effect size come from sklearn's iterative CCA,
# which stops at its own tolerance (largest measured relative gap 3.1e-9).
PILLAI_STAT_REL_TOL = 1e-8
# pgmpy computes the p-value as 1 - cdf, which floors near 1e-16 in absolute
# terms, so the p-value gets an absolute floor, else the fixture's relative 1e-9.
PILLAI_P_ABS_FLOOR = 1e-15
PILLAI_P_REL_TOL = 1e-9
MISSING = object()
DISCRETE_TESTS = {
    "chi_squared",
    "log_likelihood",
    "cressie_read",
    "freeman_tukey",
    "modified_likelihood",
}


def build_kernel(spec: dict[str, Any] | None) -> Any:
    """Map a fixture kernel description to sklearn kernels (imported lazily)."""
    if spec is None:
        return None
    if "columns" in spec:
        return {name: build_kernel(column) for name, column in spec["columns"].items()}
    kernels = importlib.import_module("sklearn.gaussian_process.kernels")
    if spec["type"] == "rbf":
        return kernels.RBF(length_scale=spec["length_scale"])
    if spec["type"] == "linear":
        return kernels.DotProduct()
    raise ValueError(f"unknown kernel type: {spec['type']}")


class LinearProbabilityModel:
    """OLS estimator for pgmpy's residualization (sklearn-compatible, no args)."""

    def get_params(self, deep: bool = True) -> dict[str, Any]:
        return {}

    def set_params(self, **params: Any) -> "LinearProbabilityModel":
        return self

    def fit(self, X: Any, y: Any) -> "LinearProbabilityModel":
        import numpy as np

        features = np.asarray(X, dtype=float)
        target = np.asarray(y)
        self._coef, *_ = np.linalg.lstsq(features, target.astype(float), rcond=None)
        classes = np.unique(target)
        indicators = (target[:, None] == classes[None, :]).astype(float)
        self._proba_coef, *_ = np.linalg.lstsq(features, indicators, rcond=None)
        return self

    def predict(self, X: Any) -> Any:
        import numpy as np

        return np.asarray(X, dtype=float) @ self._coef

    def predict_proba(self, X: Any) -> Any:
        import numpy as np

        return np.asarray(X, dtype=float) @ self._proba_coef


Constructor = Callable[[ModuleType, Any, dict[str, Any]], Any]
CONSTRUCTORS: dict[str, Constructor] = {
    "chi_squared": lambda m, df, p: m.ChiSquare(data=df),
    "log_likelihood": lambda m, df, p: m.LogLikelihood(data=df),
    "cressie_read": lambda m, df, p: m.PowerDivergence(data=df, lambda_="cressie-read"),
    "freeman_tukey": lambda m, df, p: m.PowerDivergence(
        data=df, lambda_="freeman-tuckey"
    ),
    "modified_likelihood": lambda m, df, p: m.ModifiedLogLikelihood(data=df),
    "pearson_correlation": lambda m, df, p: m.Pearsonr(data=df),
    "pearson_equivalence": lambda m, df, p: m.PearsonrEquivalence(
        data=df, delta_threshold=p["delta_threshold"]
    ),
    "fisher_z": lambda m, df, p: m.FisherZ(data=df),
    "hsic": lambda m, df, p: m.HSIC(
        data=df,
        kernel=build_kernel(p["kernel"]),
        bandwidth=p["bandwidth"],
        null_dist=p["null_dist"],
    ),
    "gcm": lambda m, df, p: m.GCM(data=df),
    "pillai": lambda m, df, p: m.PillaiTrace(
        data=df, estimator=LinearProbabilityModel()
    ),
    "kci": lambda m, df, p: m.KCI(
        data=df,
        kernel=build_kernel(p["kernel"]),
        bandwidth=p["bandwidth"],
        epsilon=p["epsilon"],
    ),
}


def should_skip(case: dict[str, Any]) -> str | None:
    """Return the single declared pgmpy parity exception, if applicable."""
    if case["test"] in DISCRETE_TESTS and case["params"].get("yates") is False:
        return "pgmpy has no Yates-disable option"
    if case["test"] == "hsic" and case["params"].get("null_dist") == "permutation":
        return "permutation null uses a different RNG than pgmpy"
    return None


def build_dataframe(case: dict[str, Any], pandas: ModuleType) -> Any:
    """Convert language-neutral fixture columns to a pandas DataFrame."""
    frame = pandas.DataFrame(
        {name: spec["values"] for name, spec in case["columns"].items()}
    )
    if case.get("test") == "pillai":
        for name, spec in case["columns"].items():
            if spec.get("kind") == "discrete":
                frame[name] = frame[name].astype("category")
    return frame


def _fields_match(
    expected: Any, actual: Any, tolerance: float, rel_tol: float | None = None
) -> bool:
    if (
        isinstance(expected, numbers.Real)
        and isinstance(actual, numbers.Real)
        and math.isfinite(float(expected))
        and math.isfinite(float(actual))
    ):
        if rel_tol is not None:
            bound = max(1e-300, rel_tol * abs(float(expected)))
            return abs(float(actual) - float(expected)) <= bound
        return math.isclose(
            float(expected), float(actual), rel_tol=0.0, abs_tol=tolerance
        )
    return bool(expected == actual)


def compare_fields(
    case_id: str,
    expected: dict[str, Any],
    actual: dict[str, Any],
    tolerance: float,
    rel_tol: float | None = None,
) -> list[str]:
    """Compare all result fields, except a dof unavailable from pgmpy."""
    errors: list[str] = []
    for field, expected_value in expected.items():
        actual_value = actual[field]
        if field == "dof" and actual_value is MISSING:
            continue
        if not _fields_match(expected_value, actual_value, tolerance, rel_tol):
            errors.append(
                f"{case_id}: {field} expected {expected_value}, got {actual_value}"
            )
    return errors


def classify_intentional_divergence(
    case: dict[str, Any], field: str, actual_value: Any
) -> str | None:
    """Classify current pgmpy's conditioned-equivalence dof propagation."""
    if (
        field == "dof"
        and case["test"] == "pearson_equivalence"
        and bool(case["z"])
        and case["expected"]["dof"] is None
        and isinstance(actual_value, numbers.Real)
        and not isinstance(actual_value, bool)
        and math.isfinite(float(actual_value))
    ):
        return (
            f"{case['id']}: dof expected None, got {actual_value} "
            "(current pgmpy propagates conditioned Pearsonr dof)"
        )
    return None


def compare_actual_fields(
    case: dict[str, Any], actual: dict[str, Any], tolerance: float
) -> tuple[list[str], list[str]]:
    """Separate strict field mismatches from declared pgmpy divergences."""
    errors: list[str] = []
    divergences: list[str] = []
    rel_tol = case.get("rel_tol")
    pillai = case.get("test") == "pillai"
    for field, expected_value in case["expected"].items():
        field_tolerance, field_rel_tol = tolerance, rel_tol
        if pillai and field in ("statistic", "effect_size"):
            field_rel_tol = PILLAI_STAT_REL_TOL
        elif pillai and field == "p_value":
            field_tolerance = max(PILLAI_P_ABS_FLOOR, PILLAI_P_REL_TOL * abs(expected_value))
            field_rel_tol = None
        field_errors = compare_fields(
            case["id"],
            {field: expected_value},
            {field: actual[field]},
            field_tolerance,
            field_rel_tol,
        )
        if not field_errors:
            continue
        divergence = classify_intentional_divergence(case, field, actual[field])
        if divergence is None:
            errors.extend(field_errors)
        else:
            divergences.append(divergence)
    return errors, divergences


def _finite_non_negative_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed) or parsed < 0.0:
        raise argparse.ArgumentTypeError("must be a finite, non-negative number")
    return parsed


def _compare_case_result(
    case: dict[str, Any], pgmpy_module: ModuleType, tolerance: float
) -> tuple[list[str], list[str]]:
    data = build_dataframe(case, importlib.import_module("pandas"))
    test = CONSTRUCTORS[case["test"]](pgmpy_module, data, case["params"])
    test.run_test(X=case["x"], Y=case["y"], Z=case["z"])
    actual = {
        "statistic": test.statistic_,
        "p_value": test.p_value_,
        "dof": getattr(test, "dof_", MISSING),
        "effect_size": test.effect_size_,
    }
    return compare_actual_fields(case, actual, tolerance)


def compare_case(
    case: dict[str, Any], pgmpy_module: ModuleType, tolerance: float
) -> list[str]:
    """Run one fixture case through pgmpy and compare every available field."""
    errors, _ = _compare_case_result(case, pgmpy_module, tolerance)
    return errors


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pgmpy-source",
        type=Path,
        help="repository root to import pgmpy from instead of the environment",
    )
    parser.add_argument(
        "--tolerance", type=_finite_non_negative_float, default=DEFAULT_TOLERANCE
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.pgmpy_source is not None:
        sys.path.insert(0, str(args.pgmpy_source.resolve()))

    pgmpy_module = importlib.import_module("pgmpy.ci_tests")
    with DEFAULT_GOLDEN.open(encoding="utf-8") as fixture:
        cases = json.load(fixture)

    compared = 0
    skipped_reasons: Counter[str] = Counter()
    errors: list[str] = []
    divergences: list[str] = []
    for case in cases:
        reason = should_skip(case)
        if reason is not None:
            skipped_reasons[reason] += 1
            continue
        compared += 1
        case_errors, case_divergences = _compare_case_result(
            case, pgmpy_module, args.tolerance
        )
        errors.extend(case_errors)
        divergences.extend(case_divergences)

    for reason, count in skipped_reasons.items():
        print(f"skipped {count}: {reason}")
    for error in errors:
        print(error)
    for divergence in divergences:
        print(f"intentional divergence: {divergence}")
    print(
        f"compared={compared} skipped={sum(skipped_reasons.values())} "
        f"divergences={len(divergences)} failed={len(errors)}"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
