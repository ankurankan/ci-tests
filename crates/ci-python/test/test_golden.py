"""Golden parity test for the data-bound Python bindings.

Loads the shared cross-language fixture ``tests/fixtures/golden.json`` and, for
each test, builds a :class:`Dataset` from the case's columns,
constructs the test with the case's parameters, runs it, and asserts that
``statistic`` / ``p_value`` / ``dof`` / ``effect_size`` match the recorded
``expected`` values.
This is the binding's numeric parity gate against the scipy/pgmpy reference.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from fastcit import (
    GCM,
    HSIC,
    KCI,
    RBF,
    ChiSquared,
    CressieRead,
    Dataset,
    FisherZ,
    FreemanTukey,
    Linear,
    LogLikelihood,
    ModifiedLikelihood,
    PearsonCorrelation,
    PearsonEquivalence,
    PillaiTrace,
)

# Locate the repo-root fixture relative to this file:
# crates/ci-python/test/test_golden.py -> repo root is three parents up.
REPO_ROOT = Path(__file__).resolve().parents[3]
GOLDEN_PATH = REPO_ROOT / "tests" / "fixtures" / "golden.json"

TOL = 1e-7

# Map the fixture's stable test name to its binding class.
TEST_CLASSES = {
    "chi_squared": ChiSquared,
    "log_likelihood": LogLikelihood,
    "cressie_read": CressieRead,
    "fisher_z": FisherZ,
    "freeman_tukey": FreemanTukey,
    "modified_likelihood": ModifiedLikelihood,
    "pearson_correlation": PearsonCorrelation,
    "pearson_equivalence": PearsonEquivalence,
    "hsic": HSIC,
    "kci": KCI,
    "gcm": GCM,
    "pillai": PillaiTrace,
}


def _load_cases() -> list[dict[str, Any]]:
    with GOLDEN_PATH.open() as fh:
        return json.load(fh)


def _build_dataset(columns: dict[str, dict[str, Any]]) -> Dataset:
    spec = {name: (col["kind"], np.asarray(col["values"], dtype=np.float64)) for name, col in columns.items()}
    return Dataset(spec)


def _kernel_obj(spec: dict[str, Any]) -> RBF | Linear:
    if spec["type"] == "rbf":
        return RBF(spec["length_scale"])
    assert spec["type"] == "linear"
    return Linear()


def _build_params(params: dict[str, Any]) -> dict[str, Any]:
    # Null-valued params are dropped so the binding defaults apply.
    out = {k: v for k, v in params.items() if v is not None}
    kernel = params.get("kernel")
    if kernel is not None:
        out["kernel"] = (
            {name: _kernel_obj(k) for name, k in kernel["columns"].items()}
            if "columns" in kernel
            else _kernel_obj(kernel)
        )
    return out


def _assert_close(actual: float | None, expected: Any, field: str, case_id: str, rel_tol: float | None = None) -> None:
    if expected is None:
        assert actual is None, f"{case_id}: expected {field}=None, got {actual!r}"
        return
    assert actual is not None, f"{case_id}: expected {field}={expected}, got None"
    exp = float(expected)
    if math.isinf(exp) or math.isnan(exp):
        # Defensive handling for inf statistic / nan (none in the current fixture).
        assert math.isinf(actual) == math.isinf(exp), f"{case_id}: {field} inf mismatch"
        assert math.isnan(actual) == math.isnan(exp), f"{case_id}: {field} nan mismatch"
        if math.isinf(exp):
            assert math.copysign(1.0, actual) == math.copysign(1.0, exp), f"{case_id}: {field} inf sign mismatch"
        return
    if rel_tol is not None:
        assert abs(actual - exp) <= max(1e-300, rel_tol * abs(exp)), (
            f"{case_id}: {field} mismatch: got {actual!r}, expected {exp!r}"
        )
        return
    assert actual == pytest.approx(exp, abs=TOL, rel=0.0), (
        f"{case_id}: {field} mismatch: got {actual!r}, expected {exp!r}"
    )


GOLDEN_CASES = _load_cases()


@pytest.mark.parametrize(
    "case",
    GOLDEN_CASES,
    ids=[case["id"] for case in GOLDEN_CASES],
)
def test_golden_case(case: dict[str, Any]) -> None:
    """Each fixture case reproduces its complete recorded result."""
    case_id = case["id"]
    assert case_id, "fixture case ID must not be empty"
    assert case["test"] in TEST_CLASSES, f"{case_id}: unknown test {case['test']}"
    data = _build_dataset(case["columns"])
    test = TEST_CLASSES[case["test"]](data, **_build_params(case["params"]))

    result = test.run_test(case["x"], case["y"], case["z"])
    expected = case["expected"]
    rel_tol = case.get("rel_tol")

    _assert_close(result.statistic, expected.get("statistic"), "statistic", case_id, rel_tol)

    _assert_close(result.p_value, expected.get("p_value"), "p_value", case_id, rel_tol)

    _assert_close(
        None if result.dof is None else float(result.dof),
        expected.get("dof"),
        "dof",
        case_id,
        rel_tol,
    )
    _assert_close(result.effect_size, expected.get("effect_size"), "effect_size", case_id, rel_tol)


def test_golden_covers_all_tests() -> None:
    """Every supported test has fixture rows, all parametrized above."""
    names = {c["test"] for c in GOLDEN_CASES}
    assert names == set(TEST_CLASSES), f"fixture tests {names} do not match binding classes {set(TEST_CLASSES)}"
