#!/usr/bin/env python3
"""Generate the language-neutral CI-test parity fixture from independent references."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import tempfile
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats
from scipy.spatial.distance import cdist, pdist

LAMBDA_BY_TEST = {
    "chi_squared": 1.0,
    "log_likelihood": 0.0,
    "cressie_read": 2.0 / 3.0,
    "freeman_tukey": -0.5,
    "modified_likelihood": -1.0,
}
DISCRETE_LAMBDAS = LAMBDA_BY_TEST
RHO_CLIP = 0.999999
CORRELATION_ZERO_ATOL = 1e-15
EXPECTED_CASE_COUNT = 121
EXPECTED_COUNTS = {
    "chi_squared": 12,
    "log_likelihood": 12,
    "cressie_read": 12,
    "freeman_tukey": 12,
    "modified_likelihood": 12,
    "pearson_correlation": 7,
    "pearson_equivalence": 6,
    "fisher_z": 7,
    "hsic": 13,
    "kci": 12,
    "gcm": 6,
    "pillai": 10,
}
KERNEL_TESTS = {"hsic", "kci"}
KERNEL_REL_TOL = 1e-9
REL_TOL_TESTS = {"hsic", "kci", "gcm", "pillai"}
BANDWIDTHS = {"heuristic", "median"}
NULL_DISTS = {"gamma", "permutation"}
CASE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
EXPECTED_KEYS = {"statistic", "p_value", "dof", "effect_size"}
DEFAULT_OUTPUT = Path(__file__).with_name("golden.json")
FIXTURE_NUMERIC_TOLERANCE = 1e-7
TOLERATED_EXPECTED_FIELDS = {"statistic", "p_value", "effect_size"}


def _column(kind: str, values: list[int] | list[float]) -> dict[str, Any]:
    return {"kind": kind, "values": values}


def _discrete_columns(
    strata: list[tuple[tuple[int, ...], list[int], list[int], list[list[int]]]],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    z_width = len(strata[0][0])
    z_names = [f"Z{i + 1}" for i in range(z_width)]
    x_values: list[int] = []
    y_values: list[int] = []
    z_values: list[list[int]] = [[] for _ in range(z_width)]
    for z_key, x_levels, y_levels, counts in strata:
        if len(z_key) != z_width or len(counts) != len(x_levels):
            raise ValueError("invalid discrete scenario shape")
        if any(len(row) != len(y_levels) for row in counts):
            raise ValueError("invalid discrete table width")
        for x_index, x_level in enumerate(x_levels):
            for y_index, y_level in enumerate(y_levels):
                count = counts[x_index][y_index]
                if count <= 0:
                    raise ValueError("active contingency cells must be positive")
                x_values.extend([x_level] * count)
                y_values.extend([y_level] * count)
                for z_index, z_level in enumerate(z_key):
                    z_values[z_index].extend([z_level] * count)
    columns = {"X": _column("discrete", x_values), "Y": _column("discrete", y_values)}
    columns.update(
        {
            name: _column("discrete", values)
            for name, values in zip(z_names, z_values, strict=True)
        }
    )
    return columns, z_names


def _discrete_scenario(
    scenario_id: str,
    yates: bool,
    strata: list[tuple[tuple[int, ...], list[int], list[int], list[list[int]]]],
) -> dict[str, Any]:
    columns, z_names = _discrete_columns(strata)
    return {
        "scenario_id": scenario_id,
        "yates": yates,
        "columns": columns,
        "x": "X",
        "y": "Y",
        "z": z_names,
    }


def _discrete_scenarios() -> list[dict[str, Any]]:
    associated = [((), [0, 1], [0, 1], [[12, 3], [4, 11]])]
    unbalanced = [((), [0, 1], [0, 1], [[18, 4], [7, 9]])]
    return [
        _discrete_scenario(
            "discrete-balanced-2x2-yates",
            True,
            [((), [0, 1], [0, 1], [[8, 8], [8, 8]])],
        ),
        _discrete_scenario("discrete-associated-2x2-yates", True, associated),
        _discrete_scenario("discrete-associated-2x2-no-yates", False, associated),
        _discrete_scenario("discrete-unbalanced-2x2-yates", True, unbalanced),
        _discrete_scenario("discrete-unbalanced-2x2-no-yates", False, unbalanced),
        _discrete_scenario(
            "discrete-2x3", True, [((), [0, 1], [0, 1, 2], [[9, 4, 7], [3, 8, 5]])]
        ),
        _discrete_scenario(
            "discrete-3x2", True, [((), [0, 1, 2], [0, 1], [[8, 3], [4, 9], [6, 5]])]
        ),
        _discrete_scenario(
            "discrete-3x3",
            True,
            [((), [0, 1, 2], [0, 1, 2], [[8, 3, 4], [5, 9, 2], [4, 6, 10]])],
        ),
        _discrete_scenario(
            "discrete-conditioned-binary",
            True,
            [
                ((0,), [0, 1], [0, 1], [[8, 3], [4, 7]]),
                ((1,), [0, 1], [0, 1], [[5, 6], [7, 4]]),
            ],
        ),
        _discrete_scenario(
            "discrete-conditioned-three-level",
            False,
            [
                ((0,), [0, 1], [0, 1], [[7, 2], [3, 6]]),
                ((1,), [0, 1], [0, 1], [[4, 5], [6, 3]]),
                ((2,), [0, 1], [0, 1], [[5, 3], [2, 8]]),
            ],
        ),
        _discrete_scenario(
            "discrete-conditioned-two-columns",
            True,
            [
                ((0, 0), [0, 1], [0, 1], [[5, 2], [3, 6]]),
                ((0, 1), [0, 1], [0, 1], [[4, 3], [5, 2]]),
                ((1, 0), [0, 1], [0, 1], [[6, 4], [2, 5]]),
                ((1, 1), [0, 1], [0, 1], [[3, 5], [6, 4]]),
            ],
        ),
        _discrete_scenario(
            "discrete-sparse-active-levels",
            True,
            [
                ((0,), [0, 1], [0, 1], [[4, 2], [3, 5]]),
                ((1,), [1, 2], [1, 2], [[2, 4], [5, 3]]),
            ],
        ),
    ]


def _strata_indices(case: dict[str, Any]) -> list[np.ndarray]:
    row_count = len(case["columns"][case["x"]]["values"])
    if not case["z"]:
        return [np.arange(row_count)]
    groups: dict[tuple[float, ...], list[int]] = {}
    for row in range(row_count):
        key = tuple(case["columns"][name]["values"][row] for name in case["z"])
        groups.setdefault(key, []).append(row)
    return [np.asarray(rows, dtype=np.int64) for rows in groups.values()]


def _discrete_expected(case: dict[str, Any], lambda_: float) -> dict[str, Any]:
    x = np.asarray(case["columns"][case["x"]]["values"])
    y = np.asarray(case["columns"][case["y"]]["values"])
    statistic = 0.0
    dof = 0
    for indices in _strata_indices(case):
        x_active = np.unique(x[indices])
        y_active = np.unique(y[indices])
        observed = np.zeros((len(x_active), len(y_active)), dtype=np.float64)
        x_index = {value: index for index, value in enumerate(x_active)}
        y_index = {value: index for index, value in enumerate(y_active)}
        for row in indices:
            observed[x_index[x[row]], y_index[y[row]]] += 1.0
        result = stats.chi2_contingency(
            observed, correction=case["yates"], lambda_=lambda_
        )
        statistic += float(result.statistic)
        dof += int(result.dof)
    p_value = float(stats.chi2.sf(statistic, dof))
    cardinality = min(len(np.unique(x)), len(np.unique(y)))
    if cardinality < 2:
        raise ValueError("degenerate discrete table: global min cardinality < 2")
    effect_size = math.sqrt(statistic / (len(x) * (cardinality - 1)))
    return {
        "statistic": statistic,
        "p_value": p_value,
        "dof": dof,
        "effect_size": effect_size,
    }


U = np.asarray(
    [
        -0.40674460841,
        -0.352511993955,
        -0.298279379501,
        -0.244046765046,
        -0.189814150591,
        -0.135581536137,
        -0.081348921682,
        -0.0271163072273,
        0.0271163072273,
        0.081348921682,
        0.135581536137,
        0.189814150591,
        0.244046765046,
        0.298279379501,
        0.352511993955,
        0.40674460841,
    ]
)
V = np.asarray(
    [
        0.463099108522,
        0.277859465113,
        0.119082627906,
        -0.0132314031006,
        -0.119082627906,
        -0.198471046509,
        -0.251396658912,
        -0.277859465113,
        -0.277859465113,
        -0.251396658912,
        -0.198471046509,
        -0.119082627906,
        -0.0132314031006,
        0.119082627906,
        0.277859465113,
        0.463099108522,
    ]
)
W = np.asarray(
    [
        -0.453244808633,
        -0.0906489617267,
        0.142448368428,
        0.265970030561,
        0.299838873404,
        0.263977745688,
        0.178309496144,
        0.0627569735031,
        -0.0627569735031,
        -0.178309496144,
        -0.263977745688,
        -0.299838873404,
        -0.265970030561,
        -0.142448368428,
        0.0906489617267,
        0.453244808633,
    ]
)
T = np.asarray(
    [
        0.398089477628,
        -0.132696492543,
        -0.322262910461,
        -0.293098846166,
        -0.14727852469,
        0.0335386739394,
        0.188108214703,
        0.275600407589,
        0.275600407589,
        0.188108214703,
        0.0335386739394,
        -0.14727852469,
        -0.293098846166,
        -0.322262910461,
        -0.132696492543,
        0.398089477628,
    ]
)


def _linear(*terms: tuple[float, np.ndarray], offset: float = 0.0) -> np.ndarray:
    values = np.full(U.shape, offset, dtype=np.float64)
    for coefficient, vector in terms:
        values += coefficient * vector
    return values


def _continuous_scenario(
    scenario_id: str, x: np.ndarray, y: np.ndarray, z: tuple[np.ndarray, ...] = ()
) -> dict[str, Any]:
    columns = {
        "X": _column("continuous", x.astype(float).tolist()),
        "Y": _column("continuous", y.astype(float).tolist()),
    }
    z_names = []
    for index, values in enumerate(z, start=1):
        name = f"Z{index}"
        columns[name] = _column("continuous", values.astype(float).tolist())
        z_names.append(name)
    return {
        "scenario_id": scenario_id,
        "columns": columns,
        "x": "X",
        "y": "Y",
        "z": z_names,
    }


def _pearson_scenarios() -> list[dict[str, Any]]:
    return [
        _continuous_scenario("orthogonal-unconditional", U, V),
        _continuous_scenario("positive-unconditional", U, _linear((0.8, U), (0.6, V))),
        _continuous_scenario("negative-unconditional", U, _linear((-0.6, U), (0.8, V))),
        _continuous_scenario(
            "confounding-removed",
            _linear((1.2, U), (0.6, V)),
            _linear((-0.9, U), (0.8, W)),
            (U,),
        ),
        _continuous_scenario(
            "residual-association",
            _linear((1.1, U), (1.0, V)),
            _linear((-0.7, U), (0.7, V), (0.3, W)),
            (U,),
        ),
        _continuous_scenario(
            "two-conditioning-columns",
            _linear((0.9, U), (-0.4, V), (0.8, W), (0.2, T)),
            _linear((-0.5, U), (0.7, V), (-0.3, W), (0.9, T)),
            (U, V),
        ),
        _continuous_scenario(
            "scale-offset-invariance",
            _linear((7.0, U), offset=10.0),
            _linear((2.0, V), offset=-3.0),
        ),
    ]


def _equivalence_scenarios() -> list[tuple[dict[str, Any], float]]:
    return [
        (_continuous_scenario("inside-orthogonal", U, V), 0.1),
        (
            _continuous_scenario(
                "inside-weak-positive",
                U,
                _linear((0.08, U), (math.sqrt(1.0 - 0.08**2), V)),
            ),
            0.2,
        ),
        (
            _continuous_scenario(
                "outside-clip-boundary",
                U,
                _linear((0.9999995, U), (math.sqrt(1.0 - 0.9999995**2), V)),
            ),
            0.1,
        ),
        (
            _continuous_scenario(
                "outside-negative",
                U,
                _linear((-0.55, U), (math.sqrt(1.0 - 0.55**2), V)),
            ),
            0.15,
        ),
        (
            _continuous_scenario(
                "inside-conditioned",
                _linear((1.2, U), (1.0, V)),
                _linear((-0.8, U), (0.05, V), (1.0, W)),
                (U,),
            ),
            0.15,
        ),
        (
            _continuous_scenario(
                "outside-two-conditioning-columns",
                _linear((0.3, U), (-0.4, V), (0.8, W), (0.2, T)),
                _linear((-0.6, U), (0.5, V), (0.1, W), (0.9, T)),
                (U, V),
            ),
            0.2,
        ),
    ]


def _fisher_scenarios() -> list[dict[str, Any]]:
    scenarios = _pearson_scenarios()[:6]
    scenarios.append(
        _continuous_scenario("perfect-correlation", U, _linear((3.0, U), offset=2.0))
    )
    return scenarios


def _partial_correlation(case: dict[str, Any]) -> tuple[float, int]:
    x = np.asarray(case["columns"][case["x"]]["values"], dtype=np.float64)
    y = np.asarray(case["columns"][case["y"]]["values"], dtype=np.float64)
    if not case["z"]:
        correlation = float(stats.pearsonr(x, y).statistic)
    else:
        z_columns = [
            np.asarray(case["columns"][name]["values"], dtype=np.float64)
            for name in case["z"]
        ]
        design = np.column_stack([np.ones(len(x)), *z_columns])
        x_beta = np.linalg.lstsq(design, x, rcond=None)[0]
        y_beta = np.linalg.lstsq(design, y, rcond=None)[0]
        correlation = float(np.corrcoef(x - design @ x_beta, y - design @ y_beta)[0, 1])
    if math.isclose(correlation, 0.0, abs_tol=CORRELATION_ZERO_ATOL):
        correlation = 0.0
    return correlation, len(x) - len(case["z"]) - 2


def _pearson_expected(case: dict[str, Any]) -> dict[str, Any]:
    correlation, dof = _partial_correlation(case)
    t_statistic = correlation * math.sqrt(dof / (1.0 - correlation**2))
    return {
        "statistic": correlation,
        "p_value": float(2.0 * stats.t.sf(abs(t_statistic), df=dof)),
        "dof": dof,
        "effect_size": abs(correlation),
    }


def _equivalence_expected(case: dict[str, Any], delta: float) -> dict[str, Any]:
    correlation, _ = _partial_correlation(case)
    rho = float(np.clip(correlation, -RHO_CLIP, RHO_CLIP))
    coefficient = math.atanh(rho)
    z_delta = math.atanh(delta)
    scale = math.sqrt(len(case["columns"][case["x"]]["values"]) - len(case["z"]) - 3)
    p_lower = 1.0 - float(stats.norm.cdf(scale * (coefficient + z_delta)))
    p_upper = float(stats.norm.cdf(scale * (coefficient - z_delta)))
    return {
        "statistic": coefficient,
        "p_value": max(p_lower, p_upper),
        "dof": None,
        "effect_size": abs(correlation),
    }


def _fisher_expected(case: dict[str, Any]) -> dict[str, Any]:
    correlation, _ = _partial_correlation(case)
    rho = float(np.clip(correlation, -RHO_CLIP, RHO_CLIP))
    scale = math.sqrt(len(case["columns"][case["x"]]["values"]) - len(case["z"]) - 3)
    statistic = scale * math.atanh(rho)
    return {
        "statistic": statistic,
        "p_value": float(2.0 * stats.norm.sf(abs(statistic))),
        "dof": None,
        "effect_size": abs(correlation),
    }


class _SplitMix64:
    """Bit-exact port of crates/ci-core/src/rng.rs (SplitMix64 + Fisher-Yates)."""

    MASK = (1 << 64) - 1

    def __init__(self, seed: int) -> None:
        self.state = seed & self.MASK

    def next_u64(self) -> int:
        self.state = (self.state + 0x9E3779B97F4A7C15) & self.MASK
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & self.MASK
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & self.MASK
        return z ^ (z >> 31)

    def bounded(self, m: int) -> int:
        threshold = ((1 << 64) - m) % m
        while True:
            r = self.next_u64()
            if r >= threshold:
                return r % m

    def shuffle_identity(self, n: int) -> list[int]:
        out = list(range(n))
        for i in range(n - 1, 0, -1):
            j = self.bounded(i + 1)
            out[i], out[j] = out[j], out[i]
        return out


def _standardize(values: Sequence[float]) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    return (array - array.mean()) / array.std(ddof=1)


def _rbf(length_scale: float) -> dict[str, Any]:
    return {"type": "rbf", "length_scale": length_scale}


def _gram(kernel: dict[str, Any], points: np.ndarray) -> np.ndarray:
    if kernel["type"] == "linear":
        return points @ points.T
    scaled = points / kernel["length_scale"]
    return np.exp(-0.5 * cdist(scaled, scaled, "sqeuclidean"))


def _median_length_scale(points: np.ndarray) -> float:
    distances = pdist(points)
    distances = distances[distances > 0.0]
    if distances.size == 0:
        return 1.0
    return float(np.median(distances)) / math.sqrt(2.0)


def _center(k: np.ndarray) -> np.ndarray:
    column_mean = k.mean(axis=0)
    return k - column_mean - column_mean[:, None] + column_mean.mean()


def _gamma_p_value(statistic: float, mean: float, var: float) -> float:
    if var <= 0.0 or mean <= 0.0:
        return 1.0
    return float(stats.gamma.sf(statistic, a=mean * mean / var, scale=var / mean))


def _explicit_kernel(choice: Any, name: str) -> dict[str, Any] | None:
    if choice is None:
        return None
    if "columns" in choice:
        return choice["columns"].get(name)
    return choice


def _hsic_heuristic_length_scale(n: int) -> float:
    return 0.8 if n < 200 else 0.5 if n < 1200 else 0.3


def _kci_heuristic_width(n: int) -> float:
    return 1.2 if n < 200 else 0.7 if n < 1200 else 0.4


def _hsic_column_kernel(
    choice: Any, name: str, points: np.ndarray, bandwidth: str
) -> dict[str, Any]:
    explicit = _explicit_kernel(choice, name)
    if explicit is not None:
        return explicit
    if bandwidth == "median":
        return _rbf(_median_length_scale(points))
    return _rbf(_hsic_heuristic_length_scale(len(points)))


def _kernel_inputs(case: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    columns = case["columns"]
    return (
        _standardize(columns[case["x"]]["values"])[:, None],
        _standardize(columns[case["y"]]["values"])[:, None],
    )


def _hsic_reference(case: dict[str, Any]) -> dict[str, Any]:
    params = case["params"]
    px, py = _kernel_inputs(case)
    kx = _gram(
        _hsic_column_kernel(params["kernel"], case["x"], px, params["bandwidth"]), px
    )
    ky = _gram(
        _hsic_column_kernel(params["kernel"], case["y"], py, params["bandwidth"]), py
    )
    return _hsic_from_grams(kx, ky, params)


def _hsic_from_grams(
    kx: np.ndarray, ky: np.ndarray, params: dict[str, Any]
) -> dict[str, Any]:
    n = len(kx)
    cx, cy = _center(kx), _center(ky)
    statistic = float(np.sum(cx * cy))
    effect_size = statistic / math.sqrt(np.sum(cx * cx) * np.sum(cy * cy))
    if params["null_dist"] == "permutation":
        rng = _SplitMix64(params["seed"])
        count = 0
        for _ in range(params["n_permutations"]):
            order = np.asarray(rng.shuffle_identity(n))
            if float(np.sum(cx * cy[np.ix_(order, order)])) >= statistic:
                count += 1
        p_value = (1.0 + count) / (1.0 + params["n_permutations"])
    elif n < 6:
        p_value = 1.0
    else:
        n_pairs = n * (n - 1.0)
        product = cx * cy
        off = (np.sum(product * product) - np.sum(np.diag(product) ** 2)) / 36.0
        factor = 72.0 * (n - 4.0) * (n - 5.0) / (n_pairs * (n - 2.0) * (n - 3.0))
        var = factor * off / n_pairs
        mu_x = (kx.sum() - np.trace(kx)) / n_pairs
        mu_y = (ky.sum() - np.trace(ky)) / n_pairs
        mean = (np.trace(kx) / n - mu_x) * (np.trace(ky) / n - mu_y) / n
        p_value = _gamma_p_value(statistic / n, n * mean, n * n * var)
    return {
        "statistic": statistic,
        "p_value": float(p_value),
        "dof": None,
        "effect_size": float(effect_size),
    }


def _kci_kernel(
    choice: Any, name: str | None, points: np.ndarray, bandwidth: str, n_z: int
) -> dict[str, Any]:
    explicit = None if name is None else _explicit_kernel(choice, name)
    if explicit is not None:
        return explicit
    if bandwidth == "median":
        return _rbf(_median_length_scale(points))
    return _rbf(_kci_heuristic_width(len(points)) * math.sqrt(n_z))


def _residualized(k: np.ndarray, rz: np.ndarray) -> np.ndarray:
    return rz @ k @ rz


def _null_factor(k: np.ndarray) -> np.ndarray:
    values, vectors = np.linalg.eigh(0.5 * (k + k.T))
    keep = values > values.max() * 1e-5
    scaled = vectors[:, keep] * np.sqrt(values[keep])
    return scaled @ scaled.T


def _kci_reference(case: dict[str, Any]) -> dict[str, Any]:
    params = case["params"]
    if not case["z"]:
        return _hsic_reference({**case, "params": {**params, "null_dist": "gamma"}})
    columns = case["columns"]
    n_z = len(case["z"])
    px, py = _kernel_inputs(case)
    pz = np.column_stack([_standardize(columns[name]["values"]) for name in case["z"]])
    x_aug = np.hstack([px, 0.5 * pz])
    choice, bandwidth = params["kernel"], params["bandwidth"]
    kernel_z = (
        choice
        if choice is not None and "type" in choice
        else _kci_kernel(None, None, pz, bandwidth, n_z)
    )
    kx = _center(_gram(_kci_kernel(choice, case["x"], x_aug, bandwidth, n_z), x_aug))
    ky = _center(_gram(_kci_kernel(choice, case["y"], py, bandwidth, n_z), py))
    kz = _center(_gram(kernel_z, pz))
    epsilon = params["epsilon"]
    n = len(kz)
    rz = epsilon * np.linalg.solve(kz + epsilon * np.eye(n), np.eye(n))
    kxr, kyr = _residualized(kx, rz), _residualized(ky, rz)
    statistic = float(np.sum(kxr * kyr))
    effect_size = statistic / math.sqrt(np.sum(kxr * kxr) * np.sum(kyr * kyr))
    u = _null_factor(kxr) * _null_factor(kyr)
    p_value = _gamma_p_value(statistic, float(np.trace(u)), 2.0 * float(np.sum(u * u)))
    return {
        "statistic": statistic,
        "p_value": p_value,
        "dof": None,
        "effect_size": float(effect_size),
    }


def _kernel_scenario(
    scenario_id: str,
    arrays: dict[str, np.ndarray],
    z_names: list[str],
    params: dict[str, Any],
    x: str = "X",
    y: str = "Y",
) -> dict[str, Any]:
    columns = {
        name: _column("continuous", [float(f"{v:.6f}") for v in values])
        for name, values in arrays.items()
    }
    return {
        "scenario_id": scenario_id,
        "columns": columns,
        "x": x,
        "y": y,
        "z": z_names,
        "params": params,
    }


def _hsic_params(
    kernel: dict[str, Any] | None = None,
    bandwidth: str = "heuristic",
    permutations: tuple[int, int] | None = None,
) -> dict[str, Any]:
    return {
        "kernel": kernel,
        "bandwidth": bandwidth,
        "null_dist": "gamma" if permutations is None else "permutation",
        "n_permutations": None if permutations is None else permutations[0],
        "seed": None if permutations is None else permutations[1],
    }


def _hsic_scenarios() -> list[dict[str, Any]]:
    def pair(seed: int, n: int, signal: Any, noise: float) -> dict[str, np.ndarray]:
        rng = np.random.default_rng(seed)
        x = rng.standard_normal(n)
        return {"X": x, "Y": signal(x) + noise * rng.standard_normal(n)}

    zero = lambda x: np.zeros_like(x)  # noqa: E731
    identity = lambda x: x  # noqa: E731
    square = lambda x: x * x  # noqa: E731
    mild = lambda x: 0.6 * x  # noqa: E731
    ties = {k: np.round(v, 1) for k, v in pair(15, 80, mild, 1.0).items()}
    cases = [
        ("hsic-independent-small", pair(11, 60, zero, 1.0), _hsic_params()),
        ("hsic-linear-dependent-small", pair(12, 60, identity, 0.5), _hsic_params()),
        ("hsic-independent-mid", pair(13, 300, zero, 1.0), _hsic_params()),
        ("hsic-nonlinear-dependent-mid", pair(14, 300, square, 0.3), _hsic_params()),
        (
            "hsic-median-bandwidth",
            pair(16, 80, mild, 1.0),
            _hsic_params(bandwidth="median"),
        ),
        ("hsic-ties-median-bandwidth", ties, _hsic_params(bandwidth="median")),
        ("hsic-rbf-all", pair(17, 80, mild, 1.0), _hsic_params(_rbf(2.0))),
        (
            "hsic-linear-all",
            pair(18, 80, mild, 1.0),
            _hsic_params({"type": "linear"}),
        ),
        (
            "hsic-per-column",
            pair(19, 80, mild, 1.0),
            _hsic_params({"columns": {"X": _rbf(0.5)}}),
        ),
        ("hsic-tiny-sample", pair(20, 5, identity, 0.5), _hsic_params()),
        ("hsic-tiny-p-value", pair(21, 250, identity, 0.7), _hsic_params()),
        (
            "hsic-permutation-independent",
            pair(22, 40, zero, 1.0),
            _hsic_params(permutations=(50, 7)),
        ),
        (
            "hsic-permutation-dependent",
            pair(23, 40, identity, 0.3),
            _hsic_params(permutations=(50, 0)),
        ),
    ]
    return [
        _kernel_scenario(scenario_id, arrays, [], params)
        for scenario_id, arrays, params in cases
    ]


def _kci_params(
    kernel: dict[str, Any] | None = None,
    bandwidth: str = "heuristic",
    epsilon: float = 1e-3,
) -> dict[str, Any]:
    return {"kernel": kernel, "bandwidth": bandwidth, "epsilon": epsilon}


def _kci_data(seed: int, n: int, n_z: int, dependent: bool) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    z = rng.standard_normal((n, n_z))
    x = z.sum(axis=1) + 0.5 * rng.standard_normal(n)
    y = 0.8 * z[:, 0] + 0.5 * rng.standard_normal(n)
    if dependent:
        y = y + 0.8 * x
    names = ["Z"] if n_z == 1 else [f"Z{i + 1}" for i in range(n_z)]
    arrays = {"X": x, "Y": y}
    arrays.update({name: z[:, i] for i, name in enumerate(names)})
    return arrays


def _kci_scenarios() -> list[dict[str, Any]]:
    one = ["Z"]
    two = ["Z1", "Z2"]
    dependent = _kci_data(32, 100, 1, True)
    cases = [
        ("kci-independent-z1-small", _kci_data(31, 100, 1, False), one, _kci_params()),
        ("kci-dependent-z1-small", dependent, one, _kci_params()),
        ("kci-independent-z1-mid", _kci_data(33, 250, 1, False), one, _kci_params()),
        ("kci-independent-z2-small", _kci_data(34, 120, 2, False), two, _kci_params()),
        ("kci-dependent-z2-small", _kci_data(35, 120, 2, True), two, _kci_params()),
        (
            "kci-median-bandwidth",
            _kci_data(36, 100, 1, True),
            one,
            _kci_params(bandwidth="median"),
        ),
        (
            "kci-rbf-all",
            _kci_data(37, 100, 1, True),
            one,
            _kci_params(_rbf(1.0)),
        ),
        (
            "kci-linear-all",
            _kci_data(38, 100, 1, True),
            one,
            _kci_params({"type": "linear"}),
        ),
        (
            "kci-per-column-z-ignored",
            _kci_data(39, 100, 1, True),
            one,
            _kci_params({"columns": {"X": _rbf(2.0), "Z": _rbf(5.0)}}),
        ),
        ("kci-empty-z", _kci_data(40, 100, 1, True), [], _kci_params()),
        ("kci-epsilon", _kci_data(41, 100, 1, True), one, _kci_params(epsilon=0.01)),
    ]
    scenarios = [
        _kernel_scenario(scenario_id, arrays, z_names, params)
        for scenario_id, arrays, z_names, params in cases
    ]
    swapped = _kernel_scenario(
        "kci-swapped", dependent, one, _kci_params(), x="Y", y="X"
    )
    scenarios.append(swapped)
    return scenarios


def _linear_design(case: dict[str, Any]) -> np.ndarray:
    """Intercept, continuous Z raw, discrete Z one-hot with first-seen level 0 dropped."""
    columns = case["columns"]
    n = len(columns[case["x"]]["values"])
    parts = [np.ones((n, 1))]
    for name in case["z"]:
        column = columns[name]
        values = np.asarray(column["values"], dtype=float)
        if column["kind"] == "discrete":
            levels = list(dict.fromkeys(values.tolist()))
            for level in levels[1:]:
                parts.append((values == level).astype(float)[:, None])
        else:
            parts.append(values[:, None])
    return np.hstack(parts)


def _residual_block(case: dict[str, Any], name: str, design: np.ndarray) -> np.ndarray:
    column = case["columns"][name]
    values = np.asarray(column["values"], dtype=float)
    if column["kind"] == "discrete":
        levels = list(dict.fromkeys(values.tolist()))
        target = np.column_stack([(values == level).astype(float) for level in levels[:-1]])
    else:
        target = values[:, None]
    beta = np.linalg.lstsq(design, target, rcond=None)[0]
    return target - design @ beta


def _gcm_reference(case: dict[str, Any]) -> dict[str, Any]:
    design = _linear_design(case)
    rx = _residual_block(case, case["x"], design)[:, 0]
    ry = _residual_block(case, case["y"], design)[:, 0]
    n = len(rx)
    u = rx * ry
    statistic = float(np.sum(u) / (math.sqrt(n) * np.std(u)))
    return {
        "statistic": statistic,
        "p_value": float(2.0 * stats.norm.sf(abs(statistic))),
        "dof": None,
        "effect_size": float(abs(np.corrcoef(rx, ry)[0, 1])),
    }


def _pillai_reference(case: dict[str, Any]) -> dict[str, Any]:
    design = _linear_design(case)
    rx = _residual_block(case, case["x"], design)
    ry = _residual_block(case, case["y"], design)
    n, p = rx.shape
    q = ry.shape[1]
    qx = np.linalg.qr(rx - rx.mean(axis=0))[0]
    qy = np.linalg.qr(ry - ry.mean(axis=0))[0]
    rho = np.linalg.svd(qx.T @ qy, compute_uv=False)
    s = min(p, q)
    v = float(np.sum(rho**2))
    df1 = p * q
    df2 = s * (n - 1 + s - p - q)
    f_stat = (v / df1) * (df2 / (s - v))
    return {
        "statistic": v,
        "p_value": float(stats.f.sf(f_stat, df1, df2)),
        "dof": None,
        "effect_size": v / s,
    }


def _linear_scenario(
    scenario_id: str,
    arrays: dict[str, np.ndarray],
    discrete: set[str],
    z_names: list[str],
    x: str = "X",
    y: str = "Y",
) -> dict[str, Any]:
    columns = {
        name: _column("discrete", [int(v) for v in values])
        if name in discrete
        else _column("continuous", [float(f"{v:.6f}") for v in values])
        for name, values in arrays.items()
    }
    return {
        "scenario_id": scenario_id,
        "columns": columns,
        "x": x,
        "y": y,
        "z": z_names,
        "params": {},
    }


def _gcm_data(
    seed: int, n: int, n_z: int, direct: float, z_effect: bool = True
) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    z = rng.standard_normal((n, n_z))
    zs = z.sum(axis=1) if z_effect else 0.0
    x = zs + rng.standard_normal(n)
    y = 0.8 * zs + direct * x + rng.standard_normal(n)
    arrays = {"X": x, "Y": y}
    names = ["Z"] if n_z == 1 else [f"Z{i + 1}" for i in range(n_z)]
    arrays.update({name: z[:, i] for i, name in enumerate(names)})
    return arrays


def _gcm_scenarios() -> list[dict[str, Any]]:
    cases = [
        ("gcm-independent-unconditional", _gcm_data(57, 150, 0, 0.0, False), []),
        ("gcm-dependent-unconditional", _gcm_data(52, 150, 0, 1.0, False), []),
        ("gcm-independent-z1", _gcm_data(53, 150, 1, 0.0), ["Z"]),
        ("gcm-dependent-z1", _gcm_data(54, 150, 1, 0.6), ["Z"]),
        ("gcm-independent-z2", _gcm_data(55, 150, 2, 0.0), ["Z1", "Z2"]),
        ("gcm-weak-effect", _gcm_data(56, 200, 1, 0.15), ["Z"]),
    ]
    return [_linear_scenario(i, a, set(), z) for i, a, z in cases]


def _levels(rng: Any, n: int, k: int, shift: np.ndarray | None = None) -> np.ndarray:
    """Discrete codes 0..k-1 from a latent score (optionally shifted)."""
    latent = rng.standard_normal(n) + (0.0 if shift is None else shift)
    cuts = np.quantile(latent, np.linspace(0, 1, k + 1)[1:-1])
    return np.searchsorted(cuts, latent).astype(int)


def _pillai_scenarios() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    def add(sid: str, arrays: dict[str, np.ndarray], disc: set[str], z: list[str]):
        out.append(_linear_scenario(sid, arrays, disc, z))

    rng = np.random.default_rng(61)
    z = rng.standard_normal(150)
    add(
        "pillai-continuous-z1",
        {
            "X": z + rng.standard_normal(150),
            "Y": 0.7 * z + rng.standard_normal(150),
            "Z": z,
        },
        set(),
        ["Z"],
    )

    rng = np.random.default_rng(62)
    x = _levels(rng, 150, 3)
    add(
        "pillai-categorical-x-continuous-y",
        {"X": x, "Y": 0.6 * x + rng.standard_normal(150)},
        {"X"},
        [],
    )

    rng = np.random.default_rng(63)
    latent = rng.standard_normal(200)
    x = np.searchsorted(np.quantile(latent, [1 / 3, 2 / 3]), latent)
    y_latent = 0.8 * latent + rng.standard_normal(200)
    y = np.searchsorted(np.quantile(y_latent, [0.25, 0.5, 0.75]), y_latent)
    add("pillai-categorical-xy", {"X": x, "Y": y}, {"X", "Y"}, [])

    rng = np.random.default_rng(64)
    z = rng.standard_normal(150)
    x = (z + rng.standard_normal(150) > 0).astype(int)
    add(
        "pillai-binary-x",
        {"X": x, "Y": 0.5 * z + 0.5 * x + rng.standard_normal(150), "Z": z},
        {"X"},
        ["Z"],
    )

    rng = np.random.default_rng(65)
    zc = rng.integers(0, 3, 200)
    add(
        "pillai-discrete-z",
        {
            "X": zc + rng.standard_normal(200),
            "Y": 0.8 * zc + rng.standard_normal(200),
            "Z": zc,
        },
        {"Z"},
        ["Z"],
    )

    for sid, seed, direct in (
        ("pillai-mixed-z", 66, 0.0),
        ("pillai-mixed-z-dependent", 67, 0.7),
    ):
        rng = np.random.default_rng(seed)
        zd = rng.integers(0, 3, 200)
        zc = rng.standard_normal(200)
        x = _levels(rng, 200, 3, 0.8 * zd + 0.5 * zc)
        y = 0.5 * zd + 0.6 * zc + direct * x + rng.standard_normal(200)
        add(sid, {"X": x, "Y": y, "ZD": zd, "ZC": zc}, {"X", "ZD"}, ["ZD", "ZC"])

    rng = np.random.default_rng(68)
    add(
        "pillai-unconditional-independent",
        {"X": rng.integers(0, 2, 150), "Y": rng.integers(0, 3, 150)},
        {"X", "Y"},
        [],
    )

    rng = np.random.default_rng(69)
    x = _levels(rng, 150, 3)
    add(
        "pillai-tiny-p-value",
        {"X": x, "Y": 1.5 * x + 1.4 * rng.standard_normal(150)},
        {"X"},
        [],
    )

    rng = np.random.default_rng(70)
    zd = rng.integers(0, 2, 150)
    x = _levels(rng, 150, 3, 0.7 * zd)
    # Recode so the first-seen order of X differs from the sorted order.
    first = list(dict.fromkeys(x.tolist()))
    remap = {level: code for code, level in enumerate(sorted(first, reverse=True))}
    x = np.array([remap[v] for v in x])
    y = 0.4 * zd + 0.4 * (x == 1) + rng.standard_normal(150)
    add("pillai-level-order", {"X": x, "Y": y, "Z": zd}, {"X", "Z"}, ["Z"])
    return out


def _case(
    case_id: str,
    test: str,
    params: dict[str, Any],
    scenario: dict[str, Any],
    expected: dict[str, Any],
    rel_tol: float | None = None,
) -> dict[str, Any]:
    case = {
        "id": case_id,
        "test": test,
        "params": params,
        "columns": scenario["columns"],
        "x": scenario["x"],
        "y": scenario["y"],
        "z": scenario["z"],
        "expected": expected,
    }
    if rel_tol is not None:
        case["rel_tol"] = rel_tol
    return case


def build_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for scenario in _discrete_scenarios():
        for test, lambda_ in LAMBDA_BY_TEST.items():
            cases.append(
                _case(
                    f"{scenario['scenario_id']}-{test.replace('_', '-')}",
                    test,
                    {"yates": scenario["yates"]},
                    scenario,
                    _discrete_expected(scenario, lambda_),
                )
            )
    for scenario in _pearson_scenarios():
        cases.append(
            _case(
                f"pearson-correlation-{scenario['scenario_id']}",
                "pearson_correlation",
                {},
                scenario,
                _pearson_expected(scenario),
            )
        )
    for scenario, delta in _equivalence_scenarios():
        cases.append(
            _case(
                f"pearson-equivalence-{scenario['scenario_id']}",
                "pearson_equivalence",
                {"delta_threshold": delta},
                scenario,
                _equivalence_expected(scenario, delta),
            )
        )
    for scenario in _fisher_scenarios():
        cases.append(
            _case(
                f"fisher-z-{scenario['scenario_id']}",
                "fisher_z",
                {},
                scenario,
                _fisher_expected(scenario),
            )
        )
    for scenario in _hsic_scenarios():
        cases.append(_kernel_case("hsic", scenario, _hsic_reference))
    for scenario in _kci_scenarios():
        cases.append(_kernel_case("kci", scenario, _kci_reference))
    for scenario in _gcm_scenarios():
        cases.append(_kernel_case("gcm", scenario, _gcm_reference))
    for scenario in _pillai_scenarios():
        cases.append(_kernel_case("pillai", scenario, _pillai_reference))
    return cases


def _kernel_case(test: str, scenario: dict[str, Any], reference: Any) -> dict[str, Any]:
    case = _case(
        scenario["scenario_id"],
        test,
        scenario["params"],
        scenario,
        {},
        KERNEL_REL_TOL,
    )
    case["expected"] = reference(case)
    return case


def _finite_number(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


def _validate_kernel_spec(case_id: str, kernel: Any, nested: bool = False) -> None:
    if kernel is None and not nested:
        return
    if isinstance(kernel, dict) and set(kernel) == {"type"}:
        if kernel["type"] == "linear":
            return
    if isinstance(kernel, dict) and set(kernel) == {"type", "length_scale"}:
        scale = kernel["length_scale"]
        if kernel["type"] == "rbf" and _finite_number(scale) and scale > 0.0:
            return
    if isinstance(kernel, dict) and set(kernel) == {"columns"} and not nested:
        columns = kernel["columns"]
        if isinstance(columns, dict) and columns:
            for entry in columns.values():
                _validate_kernel_spec(case_id, entry, nested=True)
            return
    raise ValueError(f"{case_id}: invalid kernel {kernel!r}")


def _validate_kernel_params(case_id: str, test: str, params: dict[str, Any]) -> None:
    keys = (
        {"kernel", "bandwidth", "null_dist", "n_permutations", "seed"}
        if test == "hsic"
        else {"kernel", "bandwidth", "epsilon"}
    )
    if set(params) != keys:
        raise ValueError(f"{case_id}: invalid {test} params")
    _validate_kernel_spec(case_id, params["kernel"])
    if params["bandwidth"] not in BANDWIDTHS:
        raise ValueError(f"{case_id}: invalid bandwidth {params['bandwidth']!r}")
    if test == "kci":
        epsilon = params["epsilon"]
        if not _finite_number(epsilon) or epsilon <= 0.0:
            raise ValueError(f"{case_id}: epsilon must be finite and > 0")
        return
    if params["null_dist"] not in NULL_DISTS:
        raise ValueError(f"{case_id}: invalid null_dist {params['null_dist']!r}")
    permutation = (params["n_permutations"], params["seed"])
    if params["null_dist"] == "gamma":
        if permutation != (None, None):
            raise ValueError(f"{case_id}: gamma null takes no permutation params")
    elif (
        not all(isinstance(v, int) and not isinstance(v, bool) for v in permutation)
        or permutation[0] < 1
        or permutation[1] < 0
    ):
        raise ValueError(f"{case_id}: invalid permutation params")


def validate_cases(cases: list[dict[str, Any]]) -> None:
    counts = Counter(case.get("test") for case in cases)
    if len(cases) != EXPECTED_CASE_COUNT or counts != Counter(EXPECTED_COUNTS):
        raise ValueError(
            f"expected the approved {EXPECTED_CASE_COUNT}-case distribution, got {dict(counts)}"
        )
    ids: set[str] = set()
    for case in cases:
        case_id = case.get("id")
        if not isinstance(case_id, str) or CASE_ID.fullmatch(case_id) is None:
            raise ValueError(f"invalid case id: {case_id!r}")
        if case_id in ids:
            raise ValueError(f"duplicate case id: {case_id}")
        ids.add(case_id)
        test = case["test"]
        params = case["params"]
        if test in LAMBDA_BY_TEST:
            if set(params) != {"yates"} or not isinstance(params["yates"], bool):
                raise ValueError(f"{case_id}: invalid discrete params")
        elif test == "pearson_equivalence":
            if set(params) != {"delta_threshold"} or not _finite_number(
                params["delta_threshold"]
            ):
                raise ValueError(f"{case_id}: invalid equivalence params")
            if not 0.0 < params["delta_threshold"] < 1.0:
                raise ValueError(f"{case_id}: delta_threshold must be in (0, 1)")
        elif test in {"pearson_correlation", "fisher_z", "gcm", "pillai"}:
            if params:
                raise ValueError(f"{case_id}: unexpected params")
        elif test in KERNEL_TESTS:
            _validate_kernel_params(case_id, test, params)
        else:
            raise ValueError(f"{case_id}: unknown test {test!r}")
        if test in REL_TOL_TESTS:
            rel_tol = case.get("rel_tol")
            if not _finite_number(rel_tol) or rel_tol != KERNEL_REL_TOL:
                raise ValueError(f"{case_id}: rel_tol must be {KERNEL_REL_TOL}")
        elif "rel_tol" in case:
            raise ValueError(f"{case_id}: unexpected rel_tol")
        columns = case["columns"]
        if not isinstance(columns, dict) or not columns:
            raise ValueError(f"{case_id}: columns must be a non-empty object")
        lengths: set[int] = set()
        for name, column in columns.items():
            if not isinstance(name, str) or column.get("kind") not in {
                "discrete",
                "continuous",
            }:
                raise ValueError(f"{case_id}: invalid column {name!r}")
            values = column.get("values")
            if (
                not isinstance(values, list)
                or not values
                or not all(_finite_number(v) for v in values)
            ):
                raise ValueError(f"{case_id}: invalid values for column {name}")
            lengths.add(len(values))
        if len(lengths) != 1:
            raise ValueError(f"{case_id}: column lengths differ")
        query = [case["x"], case["y"], *case["z"]]
        if len(query) != len(set(query)) or any(name not in columns for name in query):
            raise ValueError(f"{case_id}: invalid query columns {query}")
        expected = case["expected"]
        if set(expected) != EXPECTED_KEYS:
            raise ValueError(f"{case_id}: result keys must be {sorted(EXPECTED_KEYS)}")
        for field in ("statistic", "p_value", "effect_size"):
            if not _finite_number(expected[field]):
                raise ValueError(f"{case_id}: {field} must be finite")
        dof = expected["dof"]
        if test in REL_TOL_TESTS and dof is not None:
            raise ValueError(f"{case_id}: {test} has no dof")
        if dof is not None and (
            isinstance(dof, bool) or not isinstance(dof, int) or dof < 0
        ):
            raise ValueError(f"{case_id}: invalid dof {dof!r}")
        if not 0.0 <= expected["p_value"] <= 1.0 or expected["effect_size"] < 0.0:
            raise ValueError(f"{case_id}: invalid probability or effect size")


def _canonicalize(value: Any) -> Any:
    if isinstance(value, float):
        rounded = float(f"{value:.12g}")
        return 0.0 if rounded == 0.0 else rounded
    if isinstance(value, list):
        return [_canonicalize(item) for item in value]
    if isinstance(value, dict):
        return {key: _canonicalize(item) for key, item in value.items()}
    return value


def render_cases(cases: list[dict[str, Any]]) -> str:
    validate_cases(cases)
    canonical = _canonicalize(cases)
    return json.dumps(canonical, indent=2, sort_keys=True, allow_nan=False) + "\n"


def write_fixture(path: Path, rendered: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, text=True
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(rendered)
        os.chmod(temporary_name, 0o644)
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def _fixture_values_match(
    committed: Any,
    generated: Any,
    path: tuple[str | int, ...] = (),
    rel_tol: float | None = None,
) -> bool:
    if type(committed) is not type(generated):
        return False
    if isinstance(generated, dict):
        if "expected" in generated:
            rel_tol = generated.get("rel_tol")
        return committed.keys() == generated.keys() and all(
            _fixture_values_match(committed[key], value, (*path, key), rel_tol)
            for key, value in generated.items()
        )
    if isinstance(generated, list):
        return len(committed) == len(generated) and all(
            _fixture_values_match(left, right, (*path, index), rel_tol)
            for index, (left, right) in enumerate(zip(committed, generated))
        )
    if (
        len(path) >= 2
        and path[-2] == "expected"
        and path[-1] in TOLERATED_EXPECTED_FIELDS
    ):
        tolerance = (
            FIXTURE_NUMERIC_TOLERANCE
            if rel_tol is None
            else max(1e-300, rel_tol * abs(generated))
        )
        return (
            _finite_number(committed)
            and _finite_number(generated)
            and abs(committed - generated) <= tolerance
        )
    return committed == generated


def check_fixture(path: Path, rendered: str) -> bool:
    if not path.exists():
        return False
    try:
        committed = json.loads(path.read_text(encoding="utf-8"))
        generated = json.loads(rendered)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    return _fixture_values_match(committed, generated)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the committed fixture without writing it",
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT, help=argparse.SUPPRESS
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    rendered = render_cases(build_cases())
    if args.check:
        if check_fixture(args.output, rendered):
            print(f"golden fixture is current: {args.output}")
            return 0
        print(
            f"golden fixture is missing or stale: {args.output}\nregenerate it with: python tests/fixtures/generate_golden.py",
            file=sys.stderr,
        )
        return 1
    write_fixture(args.output, rendered)
    print(f"wrote {EXPECTED_CASE_COUNT} golden cases: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
