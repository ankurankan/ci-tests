# GCM and PillaiTrace for ci-tests — design

Date: 2026-11-16 · Status: awaiting approval (builder check: nothing important left) · Branch: `feature/gcm-pillai` (off `main` at `d1878c3`,
which already contains HSIC/KCI)

## Intent

Continue porting pgmpy's conditional-independence tests to the Rust core (`ci_core`) and its Python
(`ci_python`), R (`cir`) and JS/WASM (`ci_js`) bindings, one batch at a time. This batch adds **GCM**
(generalized covariance measure, continuous data) and **PillaiTrace** (Pillai's trace on regression residuals,
pgmpy's default test for **mixed** data — ci-tests has no mixed-data test today).

Why: parity with pgmpy's test catalog, so ci-tests can serve as a fast engine for constraint-based causal
discovery, now including mixed discrete/continuous data.

Owner's decision: residualization is **linear**, built into Rust and identical in every binding (no sklearn
estimators). Build on a new branch off `main`.

Reference implementation: pgmpy `cf069b04` (the commit pinned in `tests/fixtures/requirements-pgmpy.txt`;
`feature/optimization` at `cd3d4bee` has identical `gcm.py`, `pillai_trace.py` and `_base.py`):
`pgmpy/ci_tests/gcm.py`, `pgmpy/ci_tests/pillai_trace.py`, `_ResidualMixin` in `pgmpy/ci_tests/_base.py`.
Read-only snapshot available via `git -C ../pgmpy show cf069b04:<path>`.

## Goals

- `Gcm` and `Pillai` in `ci_core`, exposed with identical features in Python, R and JS.
- GCM matches pgmpy's **default** GCM (which is already linear) to fixture tolerance.
- Pillai matches pgmpy's Pillai **when pgmpy is given the same linear residualization** (see Parity), to the
  accuracy of pgmpy's iterative CCA.
- Golden-fixture cases from an independent numpy/scipy reference, checked by all four harnesses; pgmpy parity via
  `check_pgmpy_parity.py`.
- Fast: no O(n²) or O(n³) work; per query O(n·d²) with d the number of design columns.

## Non-goals

- Any sklearn estimator / random forest / XGBoost residualization (pgmpy's Pillai default is a random forest; this
  version deliberately differs). A Python-only `estimator=` path can be layered on later.
- Multinomial logistic regression for categorical targets (see "Categorical targets").
- The other remaining pgmpy tests (Hotelling–Lawley, Roy, Wilks, GeneralizedCov, IndependenceMatch, full
  PowerDivergence).
- Ordinal-specific handling (pgmpy treats ordinal like categorical in Pillai; ci-tests has no ordinal kind).

## Anti-goals

- Silent divergence from pgmpy beyond what this document declares.
- A Rust panic escaping into Python, R or JS.

## Constraints

- Everything already on `main`: `CITest::validate` hook, `CiError::InvalidConfig`, the per-case `rel_tol`
  fixture rule, faer 0.24 (available but not required here), R MSRV 1.85, the platform-filtered R vendor archive
  (must not change — no new crates), the pgmpy pin `cf069b04`.
- The R package must stay < 5 MB built; no new dependencies anywhere.
- Fixture comparisons: new cases carry `"rel_tol": 1e-9` (rule `|a − e| ≤ max(1e-300, rel_tol·|e|)`), existing
  cases unchanged.
- R is verified locally in conda env `cir-dev`; nothing is pushed until the owner asks.

## Approaches (residualization for Pillai — owner's decision)

1. **Linear residualization built into Rust — chosen.** Fast, deterministic, identical across bindings. Does not
   reproduce pgmpy's random-forest default and does not adjust for nonlinear effects of Z.
2. Python computes residuals with any sklearn model; Rust does only CCA + F-test. Exact pgmpy parity in Python, but
   the forest dominates run time and R/JS get only the linear version. Not chosen.
3. Both. Most flexible, most work. Deferred (can be added on top of 1).

GCM needs no decision: pgmpy's default is already linear regression.

## Design

### Shared: linear residualization (crate-private module, e.g. `crate::residual`)

- **Design matrix for Z** (n × d): intercept column, then each continuous Z column as is, then each discrete Z
  column one-hot encoded with one level dropped. This spans exactly the same space as pgmpy's
  `pd.get_dummies([Z, intercept])` (all levels + intercept) fitted with `LinearRegression`, so fitted values are
  identical; dropping a level just avoids the exact collinearity. Empty Z → intercept only (residual = centered
  target).
- **Fit**: ordinary least squares for many targets at once, via the existing Householder-QR approach in
  `crates/ci-core/src/correlation.rs::ols_residuals` generalized to multiple right-hand sides (or a Cholesky
  solve of `DᵀD` — builder's call, as long as accuracy matches the reference to 1e-9 relative). A rank-deficient
  design (e.g. a discrete Z level that is constant, or n ≤ d) → `CiError::DegenerateData` (today's
  `ols_residuals` returns `Numeric` for this; map it for the new tests without changing the existing tests'
  errors).
- **Continuous target**: residual `r = t − t̂`.
- **Categorical target** with K observed levels (my call: *linear probability model*): regress each level's 0/1
  indicator column on the design by OLS; residual matrix = indicators − fitted (n × K); keep K − 1 columns (drop
  the last level in first-appearance order, mirroring pgmpy's `iloc[:, :-1]`). Because the design has an
  intercept, the fitted values of the K indicators sum to 1 per row, so any K − 1 columns span the same space and
  the choice of dropped level does not change the Pillai statistic. K = 1 → `DegenerateData`.
  - Why LPM, not multinomial logistic: it is the linear model the owner asked for, closed form with no
    convergence or separation failures, and reuses the OLS path. Fitted "probabilities" may fall outside
    [0, 1]; that is harmless for residual correlations.

### GCM (port of pgmpy `gcm.py` with its default `LinearRegression`)

- Data: continuous only (X, Y, Z); discrete → `WrongColumnKind`.
- `r_x`, `r_y` = OLS residuals on `[1, Z]`; `U = r_x ∘ r_y`;
  `T = (1/√n) · ΣU / std(U)` with `std` the population standard deviation (`np.std`, ddof = 0);
  `p = 2·Φ̄(|T|)` (standard normal upper tail); `effect_size = |corr(r_x, r_y)|`; `dof = None`;
  `statistic = T` (signed).
- `std(U) = 0` or a constant residual → `DegenerateData` (pgmpy would return NaN — declared divergence).
- Meta: name `"gcm"`, `data_types = [Continuous]`, symmetric, `PValueGe`. No configuration.

### Pillai (port of pgmpy `pillai_trace.py` with linear residualization)

- Data: X, Y, Z each discrete or continuous (mixed allowed).
- `R_x` (n × p), `R_y` (n × q) from the shared residualization; `s = min(p, q)`.
- Pillai's trace `V = Σ ρ_i²` over the canonical correlations of `R_x` and `R_y`, computed exactly:
  `V = tr(S_xx⁻¹ S_xy S_yy⁻¹ S_yx)` on column-centered residuals (no eigendecomposition needed for the trace).
  Singular `S_xx` or `S_yy` (a residual column with no variance, e.g. X determined by Z) → `DegenerateData`.
- F-approximation exactly as pgmpy: `df1 = p·q`, `df2 = s·(n − 1 + s − p − q)`,
  `F = (V/df1)·(df2/(s − V))`, `p = F_sf(F; df1, df2)` (survival function, not `1 − cdf`, for tail accuracy;
  verify statrs' F survival function against scipy in the far tail and fall back to the regularized incomplete
  beta if it is not accurate);
  `effect_size = V/s`; `statistic = V`; `dof = None`. `V ≥ s` (numerically) → `p = 0`; `df2 ≤ 0` →
  `DegenerateData`.
  - Note (kept for parity): pgmpy's `df2` ignores the number of conditioning columns, so for large |Z| relative to
    n it is slightly anti-conservative. Document, do not "fix".
- Meta: name `"pillai"`, `data_types = [Discrete, Continuous]`, symmetric, `PValueGe`. No configuration.

### Core API

- `ci_core::ci_tests::{Gcm, Pillai}` — unit structs with `new()`/`Default` (type names are the builder's call
  within clippy's acronym rule). Registry gains both (12 tests).
- `CiResult`: statistic, p-value, effect size; `dof = None` for both.

### Bindings (no configuration options for either test)

- Python: `ci_python.GCM(data)`, `ci_python.PillaiTrace(data)` (pgmpy's class names); exports, stub, README.
- R: `gcm(data)`, `pillai(data)` (R factory names equal the stable test names, as for every other test);
  extendr handles, roxygen, NAMESPACE, man pages regenerated in `cir-dev`.
- JS: `new GCM(data)`, `new PillaiTrace(data)` with `EmptyConfig`; TypeScript types; README.

### Fixtures and parity

- `generate_golden.py`: independent numpy/scipy reference (`numpy.linalg.lstsq` residuals; canonical correlations
  via QR + SVD; `scipy.stats.f.sf`, `scipy.stats.norm.sf`). Cases (exact data the builder's call), all with
  `rel_tol: 1e-9`:
  - GCM (~6): independent, dependent, |Z| = 0, 1, 2, a weak-effect case.
  - Pillai (~10): continuous X/Y with continuous Z; categorical X (K = 3) with continuous Y; categorical X and Y;
    binary X; discrete Z; mixed Z (one discrete, one continuous); |Z| = 0; a dependent case with a tiny p-value;
    a case whose categorical X has a level dropped in some Z level (exercises first-appearance order).
- `check_pgmpy_parity.py`:
  - GCM: pgmpy `GCM(data)` default; strict tolerance.
  - Pillai: pgmpy `PillaiTrace(data, estimator=<linear-probability wrapper>)`, a small sklearn-compatible class
    (fit → OLS; `predict` for continuous targets; `predict_proba` = OLS on the target's one-hot columns) so pgmpy
    computes the same residuals. Discrete fixture columns must be passed to pgmpy as `category` dtype for these
    cases. Compare with a declared looser tolerance for Pillai (pgmpy's sklearn CCA is iterative, tol 1e-6;
    builder measures the actual gap and sets the tolerance just above it).
  - pgmpy computes Pillai's p-value as `1 − cdf`, which floors near 1e-16; the tiny-p Pillai case is compared
    with an absolute tolerance (or declared as a skip) in the parity checker — my call.
  - Bump nothing (pin already `cf069b04`).
- `generate_golden.py` today accepts `rel_tol` only on hsic/kci cases and validates params per test: extend the
  validator so `gcm`/`pillai` cases require `rel_tol` and empty params.

### Documentation

README "Available Tests" table (+ mixed-data note), `ci_core` crate docs (table, counts ten → twelve), binding
READMEs, and the declared pgmpy differences: linear residualization only (pgmpy's Pillai default is a random
forest), LPM for categorical targets, exact CCA, degenerate inputs raise instead of NaN.

### Verification

`cargo fmt --check`, `cargo clippy --all-targets -D warnings`, `cargo test -p ci_core`; repo `tests/`;
`generate_golden.py --check`; `sync_package_assets.py --check`; Python (scratchpad wheel, never into the `pgmpy`
env), JS (`~/.cargo/bin/wasm-pack`, `npm test`), R (`cir-dev`: `devtools::test`, `R CMD build` < 5 MB,
`R CMD check --as-cran`); `check_pgmpy_parity.py` against `cf069b04`; quick per-query timing vs pgmpy
(`feature/optimization`) on alarm (discrete), the 30-variable Gaussian data, and a mixed dataset.

## Left to the builder

- Module layout, helper names, QR vs Cholesky for the multi-target OLS (accuracy requirement above).
- Exact fixture data and seeds.
- The measured Pillai parity tolerance.
- Whether to cache the Z design factorization across queries with the same Z (optional optimization; must not
  change results).

## Risks

- sklearn CCA's iterative solution may differ from the exact trace by more than expected for multi-column blocks;
  the parity tolerance must be set from measurement, not assumed.
- pgmpy's `preprocess_data` may classify integer-coded columns as numeric; the parity checker must cast discrete
  columns to `category`.
- Rank-deficient designs in real data (rare levels of a discrete Z) will raise; this is intended but should be
  documented.
