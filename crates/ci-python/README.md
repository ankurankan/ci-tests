# FastCIT: Fast Conditional Independence Tests (Python)

Python bindings for the [Conditional Independence Testing](../../README.md) library.
Wraps the data-bound Rust core via [PyO3](https://pyo3.rs).

The API is **data-bound**: build a `Dataset` once from named, typed columns, then
construct any test bound to that data and query it with `run_test` /
`is_independent`. Each test declares its own independence rule, so the caller never
writes the `p >= alpha` (vs. `p < alpha`) logic.

## Available tests

| Class | Data type | Constructor config | `dof` |
|---|---|---|---|
| `ChiSquared` | Discrete | `yates=True` | int |
| `LogLikelihood` | Discrete | `yates=True` | int |
| `CressieRead` | Discrete | `yates=True` | int |
| `FreemanTukey` | Discrete | `yates=True` | int |
| `ModifiedLikelihood` | Discrete | `yates=True` | int |
| `PearsonCorrelation` | Continuous | — | `n - |Z| - 2` |
| `PearsonEquivalence` | Continuous | `delta_threshold=0.1` | `None` |
| `FisherZ` | Continuous | — | `None` |
| `GCM` | Continuous | — | `None` |
| `PillaiTrace` | Mixed (discrete and continuous) | — | `None` |
| `HSIC` | Continuous | `kernel=None`, `bandwidth="heuristic"`, `null_dist="gamma"`, `n_permutations=100`, `seed=0` | `None` |
| `KCI` | Continuous | `kernel=None`, `bandwidth="heuristic"`, `epsilon=1e-3` | `None` |

`run_test` returns a `CiResult` with attributes `statistic` (float | None),
`p_value` (float), `dof` (int | None), and `effect_size` (float | None).
`PearsonCorrelation` reports `dof = n - |Z| - 2`; Fisher-Z and Pearson
equivalence report `None`.

### GCM and PillaiTrace

```python
from fastcit import GCM, PillaiTrace

GCM(data).run_test("X", "Y", ["Z"])  # continuous columns only
PillaiTrace(df).run_test("X", "Y", ["Z", "G"])  # mixed discrete/continuous
```

Neither takes configuration. Both residualize `X` and `Y` on `Z` with **linear
regression**, whereas pgmpy's default regressor is a random forest, so
p-values differ from pgmpy defaults. In `PillaiTrace`, discrete conditioning
variables are one-hot encoded minus one level, and a categorical `X` or `Y`
becomes K-1 level indicators residualized with a linear probability model;
canonical correlations are exact. `GCM` raises `CiError` for any discrete
column; `PillaiTrace` raises `CiError` on degenerate data (e.g. `X` fully
determined by `Z`). Conditioning sets whose columns are linearly dependent (duplicate or nested categorical variables, a constant column) raise a degenerate-data error, whereas pgmpy fits them by least squares. When `Z` is not empty and
`n - columns == max(p, q)`, `PillaiTrace` returns `p = 0` ("dependent"), as pgmpy
does. When `n - columns < max(p, q)`, it raises an error.

### Kernel tests (HSIC and KCI)

```python
from fastcit import Dataset, HSIC, KCI, RBF, Linear

# Marginal independence (HSIC takes no conditioning set) and conditional (KCI).
hsic = HSIC(data, kernel=RBF(1.0), null_dist="permutation", n_permutations=200, seed=1)
hsic.run_test("X", "Y")
kci = KCI(data, kernel={"X": RBF(2.0), "Y": Linear(), "Z": RBF(0.5)})
kci.run_test("X", "Y", ["Z"])
```

`kernel` is `None` (automatic), a single `RBF`/`Linear` applied to all columns,
or a `dict` mapping column names to kernels. Differences from pgmpy: the
permutation RNG is an integer `seed` (not `rng`), and only the `RBF` and
`Linear` kernels are supported. Invalid configuration (e.g. `epsilon <= 0`,
non-positive length scale, unknown column in `kernel`) raises `CiError` at
construction.

## Requirements

- Python 3.10 to 3.14
- NumPy
- Rust (stable), installed via [rustup](https://rustup.rs)
- [maturin](https://www.maturin.rs) 1.11 or later

## Installation

From the repository root:

```bash
pip install maturin
maturin develop -m crates/ci-python/Cargo.toml
```

> On Python 3.14 with PyO3 0.24, build with
> `PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1` set (the crate already requests the
> `abi3-py310` feature).

## Usage

```python
import numpy as np
from fastcit import Dataset, ChiSquared, FisherZ, PearsonEquivalence

data = Dataset(
    {
        "A": ("discrete", np.array([0, 1, 0, 1, 0, 1, 1, 0], dtype=float)),
        "B": ("discrete", np.array([1, 1, 0, 0, 1, 0, 1, 0], dtype=float)),
        "C": ("discrete", np.array([0, 0, 1, 1, 0, 1, 0, 1], dtype=float)),
        "X": ("continuous", np.random.default_rng(0).standard_normal(8)),
        "Y": ("continuous", np.random.default_rng(1).standard_normal(8)),
        "Z": ("continuous", np.random.default_rng(2).standard_normal(8)),
    }
)

# Discrete: chi-squared with Yates' correction (the default).
chi = ChiSquared(data)  # yates=True
res = chi.run_test("A", "B", ["C"])  # A ⟂ B | C
res.statistic, res.p_value, res.dof, res.effect_size
chi.is_independent("A", "B", ["C"], significance_level=0.05)  # -> bool (p >= alpha)

# Continuous Fisher-Z and equivalence (TOST): every query column is continuous.
fz = FisherZ(data)
fz_res = fz.run_test("X", "Y", ["Z"])
assert fz_res.dof is None
eqv = PearsonEquivalence(data, delta_threshold=0.1)
res = eqv.run_test("X", "Y", ["Z"])  # res.dof is None
eqv.is_independent("X", "Y", ["Z"], significance_level=0.05)  # -> bool (p < alpha)
```

- `x` and `y` accept a column **name** (`str`) or an integer **index**; `z` is a
  sequence of names/indices (default: empty conditioning set).
- A test constructor accepts either a `Dataset` or a raw
  `{name: (kind, values)}` mapping.
- Core errors (degenerate data, wrong column kind, …) raise `fastcit.CiError`;
  unknown columns / out-of-range indices raise `ValueError`.

### From a pandas DataFrame

`Dataset.from_pandas` infers kinds from dtypes (integer / bool / categorical →
discrete, float → continuous). `pandas` is imported lazily and is not a hard
dependency of the package.

```python
import pandas as pd
from fastcit import Dataset, ChiSquared

df = pd.DataFrame({"A": [0, 1, 0, 1], "B": [1, 1, 0, 0]})
ChiSquared(Dataset.from_pandas(df)).run_test("A", "B")
```

## Running tests

```bash
pip install -e "crates/ci-python[test]"
pytest crates/ci-python/test
```

The golden test (`test/test_golden.py`) checks numeric parity against the shared
scipy/pgmpy fixture (`tests/fixtures/golden.json`).

## License

Licensed under the [MIT license](../../LICENSE).
