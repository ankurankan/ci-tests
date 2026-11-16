# GCM and PillaiTrace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port pgmpy's GCM and PillaiTrace (with linear residualization) into `ci_core` and expose them in the Python, R and JS bindings with golden-fixture and pgmpy-parity coverage.

**Architecture:** A crate-private `residual` module builds the `[1, Z]` design (continuous Z raw, discrete Z one-hot minus one level), turns each target into a block (continuous: one column; discrete: K−1 level indicators), and returns OLS residuals for all target columns at once. `Gcm` and `Pillai` are unit-struct `CITest`s on top of it; Pillai's trace is computed exactly as `tr(Sxx⁻¹ Sxy Syy⁻¹ Syx)`. Bindings add config-less classes.

**Tech Stack:** Rust 2021 (`faer` 0.24 and `statrs` 0.18 already in `ci_core`), PyO3/maturin, extendr/R (conda env `cir-dev`), wasm-bindgen + vitest, Python fixture tooling (numpy, scipy).

**Spec:** `docs/superpowers/specs/2026-11-16-gcm-pillai-design.md` — normative for every formula below. pgmpy reference: commit `cf069b04` (`git -C ../pgmpy show cf069b04:pgmpy/ci_tests/gcm.py`, `.../pillai_trace.py`, `.../_base.py`).

## Global Constraints

- Branch `feature/gcm-pillai` (off `main` `d1878c3`, design committed as `63a3258`). Commit locally after each task; **never push, never open a PR** until the owner asks.
- Every commit message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- No new dependencies anywhere; the R vendor archive and both `Cargo.lock` files must not change.
- Linear residualization only; no estimator option in any binding. Categorical targets use the linear probability model (OLS on level indicators).
- Test names `"gcm"` and `"pillai"`; Python classes `GCM`, `PillaiTrace`; R `gcm()`, `pillai()`; JS classes `GCM`, `PillaiTrace`. Neither test has configuration.
- `dof = None` for both tests. Degenerate inputs raise `CiError::DegenerateData` (never NaN, never a panic); GCM on a discrete column raises `CiError::WrongColumnKind`.
- After any change under `crates/ci-core/**` or `tests/fixtures/golden.json`, run `python crates/ci-r/tools/sync_package_assets.py --sync` and commit the R copies in the same commit.
- New fixture cases carry `"rel_tol": 1e-9`; existing cases unchanged; `golden.json` grows ≤ 150 000 bytes over 308 638; continuous fixture data rounded to 6 decimals.
- Python is built and tested only via a scratchpad wheel (`maturin build --release ... -o <scratchpad>/wheels`, `pip install --target <scratchpad>/site --no-deps`), never installed into the `pgmpy` conda env. Scratchpad: `/tmp/claude-1000/-home-ankur-work-pgmpy-ci-tests/1caf9050-6f9c-4107-a19b-c282dc5333a9/scratchpad`.
- JS uses `~/.cargo/bin/wasm-pack` (`/usr/bin/wasm-pack` is an empty placeholder). R runs in `cir-dev` with `LD_LIBRARY_PATH=$CONDA_PREFIX/lib/R/lib:$CONDA_PREFIX/lib`.
- Lints as today: `cargo fmt`, clippy pedantic `-D warnings`, ruff, eslint/prettier, lintr/styler.

## Review Focus

1. **Rank-deficient design** — a discrete Z level that occurs only where another Z column is constant, two identical Z columns, or n ≤ number of design columns: `DegenerateData` naming the problem, not `Numeric` and not a panic — test in Task 1.
2. **X fully determined by Z** (categorical or continuous X equal to a function of Z's levels): the residual block has no variance → `DegenerateData` — test in Task 3 (Pillai) and Task 2 (GCM, continuous).
3. **Categorical target with a single observed level**: `DegenerateData` — test in Task 1.
4. **Perfect dependence** (continuous Y identical to X, or categorical Y a relabelling of X): `V` hits `s`, `p = 0`, finite statistic, no error — test in Task 3.
5. **GCM given a discrete X, Y or Z column**: `WrongColumnKind` — test in Task 2.

---

### Task 1: Linear residualization module

**Files:**
- Create: `crates/ci-core/src/residual.rs`
- Modify: `crates/ci-core/src/lib.rs` (`mod residual;`)

**Interfaces:**
- Produces (crate-private), all row-major `faer::Mat<f64>`:
  - `pub(crate) fn design_matrix(data: &Dataset, z: &[usize]) -> Result<Mat<f64>, CiError>` — columns: intercept, then for each `z` entry in order either its continuous values or, for a discrete column with K observed levels, indicators of levels `1..K` (level code 0 dropped).
  - `pub(crate) fn target_block(data: &Dataset, col: usize) -> Result<Mat<f64>, CiError>` — continuous: n×1 values; discrete with K levels: indicators of codes `0..K-1` (n × (K−1), the last code dropped); K = 1 → `DegenerateData("column … has a single observed level")`.
  - `pub(crate) fn ols_residuals_multi(design: MatRef<'_, f64>, targets: MatRef<'_, f64>) -> Result<Mat<f64>, CiError>` — OLS residuals of every target column on `design`; rank-deficient design (zero/near-zero pivot, relative tolerance 1e-10 of the largest pivot) or `n <= d` → `DegenerateData("design matrix [1, Z] is rank-deficient …")`.
- Consumes: `Dataset::continuous(idx)` / `Dataset::discrete(idx)` (codes are first-seen order, `0..cardinality`).

- [ ] **Step 1: Write failing unit tests in `residual.rs`**

```rust
#[test] fn empty_z_residuals_are_centered_targets() { /* design = ones(n,1); residual of [1,2,3,6] == [-2,-1,0,3] (1e-12) */ }
#[test] fn residuals_are_orthogonal_to_design() { /* random continuous + discrete Z: Dᵀ·R ≈ 0 (1e-9 relative to ‖R‖) */ }
#[test] fn discrete_z_one_hot_matches_full_dummies_fit() {
    // residuals from design_matrix(discrete Z with 3 levels) equal residuals from a design built with ALL 3
    // level indicators and no intercept (same column space), to 1e-12
}
#[test] fn discrete_target_block_drops_last_level() { /* codes [0,1,2,0,2]: block columns are indicators of codes 0 and 1 */ }
#[test] fn single_level_target_is_degenerate() { /* DegenerateData */ }
#[test] fn rank_deficient_design_is_degenerate() { /* Z = [a, a] (identical continuous columns) -> DegenerateData; n=3 with 3 Z columns -> DegenerateData */ }
#[test] fn multi_target_matches_single_target_fits() { /* residualizing [t1 t2] at once == each alone (1e-12) */ }
```

- [ ] **Step 2: Run to see them fail** — `cargo test -p ci_core residual` → compile errors.
- [ ] **Step 3: Implement** with Householder QR on the design (generalizing `correlation.rs::ols_residuals`, which stays unchanged) or a Cholesky solve of `DᵀD`; either must meet the 1e-12 tests above. Add a scoped `#[allow(dead_code)]` with comment "used by GCM/Pillai (Tasks 2–3)" until consumers exist.
- [ ] **Step 4: Run** — `cargo test -p ci_core && cargo clippy -p ci_core --all-targets -- -D warnings && cargo fmt --check` → PASS.
- [ ] **Step 5: Sync + commit** — `python crates/ci-r/tools/sync_package_assets.py --sync`; `git commit -m "feat(core): add linear residualization helpers"`

---

### Task 2: GCM in the core

**Files:**
- Create: `crates/ci-core/src/ci_tests/gcm.rs`
- Modify: `crates/ci-core/src/ci_tests/mod.rs`, `crates/ci-core/src/registry.rs`

**Interfaces:**
- Consumes: Task 1 `design_matrix`, `ols_residuals_multi`.
- Produces: `#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)] pub struct Gcm;` with `Gcm::new()`; re-export `pub use gcm::Gcm;`; registry entry; `meta()` = name `"gcm"`, `data_types: &[DataType::Continuous]`, `symmetric: true`, `PValueGe`.

- [ ] **Step 1: Failing tests (unit tests in `gcm.rs`; registry `EXPECTED_NAMES` gains `"gcm"`)**

```rust
#[test] fn unconditional_matches_closed_form() {
    // x̃, ỹ centered; u = x̃∘ỹ; T = sum(u) / (sqrt(n) * std_pop(u)); p = 2*Φ̄(|T|); effect = |pearson r|
    // all to 1e-12 on a fixed 40-row dataset; dof None
}
#[test] fn conditional_uses_ols_residuals() { /* |Z|=2: same formula on residuals from an independent normal-equations fit in the test (1e-10) */ }
#[test] fn symmetric_in_x_and_y() { /* identical statistic/p/effect when swapped */ }
#[test] fn discrete_column_is_wrong_kind() { /* discrete X, Y or Z -> WrongColumnKind */ }
#[test] fn x_determined_by_z_is_degenerate() { /* X = 2Z+1 exactly, z=[Z] -> DegenerateData (residual has no variance) */ }
```

- [ ] **Step 2: Run to see them fail** — `cargo test -p ci_core gcm registry`.
- [ ] **Step 3: Implement** per the spec's "GCM" section (normal tail via `statrs::distribution::Normal` sf; `std(U) == 0` → `DegenerateData`).
- [ ] **Step 4: Run** — `cargo test -p ci_core` + clippy + fmt → PASS.
- [ ] **Step 5: Sync + commit** — `git commit -m "feat(core): add GCM test"`

---

### Task 3: PillaiTrace in the core, plus core docs

**Files:**
- Create: `crates/ci-core/src/ci_tests/pillai.rs`
- Modify: `crates/ci-core/src/ci_tests/mod.rs`, `crates/ci-core/src/registry.rs`, `crates/ci-core/src/lib.rs` (crate-doc table rows for GCM and Pillai; "ten" → "twelve"), `crates/ci-core/README.md`, root `README.md` ("Available Tests" rows for `gcm` and `pillai`, a mixed-data note, and the declared pgmpy differences from the spec's Documentation section)

**Interfaces:**
- Consumes: Task 1 helpers.
- Produces: `#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)] pub struct Pillai;` with `Pillai::new()`; re-export `pub use pillai::Pillai;`; registry entry (12 names); `meta()` = name `"pillai"`, `data_types: &[DataType::Discrete, DataType::Continuous]`, `symmetric: true`, `PValueGe`; crate-private `fn pillai_trace(rx: MatRef<'_, f64>, ry: MatRef<'_, f64>) -> Result<f64, CiError>`.

- [ ] **Step 1: Failing tests in `pillai.rs`**

```rust
#[test] fn continuous_pair_matches_squared_pearson() {
    // z = []: V == r^2 (1e-12); p == PearsonCorrelation p-value on the same data (1e-10); effect == V
}
#[test] fn categorical_vs_continuous_is_one_way_anova() {
    // X categorical with K=3 levels, Y continuous, z = []: V == SSB/SST (1e-12) and
    // p == FisherSnedecor(K-1, n-K).sf(F_anova) (1e-10)
}
#[test] fn mixed_conditioning_runs_and_is_symmetric() { /* X cat, Y cont, Z = [discrete, continuous]; swap x/y -> identical V and p */ }
#[test] fn perfect_dependence_gives_p_zero() { /* Y identical to X (continuous) and Y a relabelling of categorical X: V == s within 1e-12, p == 0.0, finite statistic */ }
#[test] fn categorical_x_determined_by_z_is_degenerate() { /* X levels a function of discrete Z -> DegenerateData */ }
#[test] fn f_tail_is_accurate() { /* FisherSnedecor(3, 200).sf(40.0) vs scipy value hard-coded (rel 1e-9); fall back to the regularized incomplete beta if this fails */ }
```
Compute the hard-coded scipy value once with `python -c "from scipy.stats import f; print(repr(f.sf(40.0, 3, 200)))"`.

- [ ] **Step 2: Run to see them fail** — `cargo test -p ci_core pillai`.
- [ ] **Step 3: Implement** per the spec's "Pillai" section: residual blocks from Task 1, column-center, `V = tr(Sxx⁻¹ Sxy Syy⁻¹ Syx)` via Cholesky of `Sxx`/`Syy` (failure or a non-positive pivot → `DegenerateData`), pgmpy's `df1`/`df2`/F exactly, `p` from the survival function, `V ≥ s` → `p = 0`, `df2 ≤ 0` → `DegenerateData`. Remove Task 1's `dead_code` allow. Update docs.
- [ ] **Step 4: Run** — `cargo test -p ci_core && cargo test -p ci_core --doc` + clippy + fmt → PASS.
- [ ] **Step 5: Sync + commit** — `git commit -m "feat(core): add PillaiTrace test and document GCM/Pillai"`

---

### Task 4: Golden fixture cases and Rust harness

**Files:**
- Modify: `tests/fixtures/generate_golden.py`, `tests/fixtures/golden.json` (regenerated), `tests/fixtures/test_generate_golden.py`, `crates/ci-core/tests/golden.rs`, R fixture copy (via sync)

**Interfaces:**
- Consumes: `Gcm`, `Pillai` from Tasks 2–3.
- Produces (fixture contract for Tasks 5–8): tests `"gcm"` and `"pillai"`, `params == {}`, `"rel_tol": 1e-9`, `dof: null`; `EXPECTED_COUNTS` gains `"gcm": 6, "pillai": 10`; `EXPECTED_CASE_COUNT = 121`.

| id | n | columns / query |
|---|---|---|
| `gcm-independent-unconditional` | 150 | X, Y continuous; z = [] |
| `gcm-dependent-unconditional` | 150 | Y = X + noise |
| `gcm-independent-z1` | 150 | X = Z + e, Y = Z + e; z = [Z] |
| `gcm-dependent-z1` | 150 | Y depends on X and Z |
| `gcm-independent-z2` | 150 | two Z |
| `gcm-weak-effect` | 200 | small direct X→Y effect |
| `pillai-continuous-z1` | 150 | X, Y, Z continuous |
| `pillai-categorical-x-continuous-y` | 150 | X 3 levels; z = [] |
| `pillai-categorical-xy` | 200 | X 3 levels, Y 4 levels; z = [] |
| `pillai-binary-x` | 150 | X 2 levels, Y continuous, Z continuous |
| `pillai-discrete-z` | 200 | X, Y continuous; Z 3 levels |
| `pillai-mixed-z` | 200 | X 3 levels, Y continuous; Z = [discrete 3 levels, continuous] |
| `pillai-mixed-z-dependent` | 200 | as above with a direct X→Y effect |
| `pillai-unconditional-independent` | 150 | X 2 levels, Y 3 levels |
| `pillai-tiny-p-value` | 150 | strong dependence; tune so 1e-40 < p < 1e-12 |
| `pillai-level-order` | 150 | categorical X whose first-seen level order differs from sorted order; Z discrete |

- [ ] **Step 1: Failing tests in `test_generate_golden.py`**: catalog contract (121 cases, new counts, every gcm/pillai case has `rel_tol == 1e-9`, `params == {}`, `dof is None`); `test_pillai_reference_matches_squared_pearson` (reference V on `pillai-continuous-z1` data with z = [] equals `pearson r**2`, 1e-12); `test_validation_rejects_params_on_gcm_and_pillai`; `test_fixture_growth_within_budget` (`len(render_cases(build_cases()).encode()) <= 308_638 + 150_000`).
- [ ] **Step 2: Run** — `python -m pytest tests/fixtures/test_generate_golden.py -q` → FAIL.
- [ ] **Step 3: Implement** the independent numpy/scipy reference (`numpy.linalg.lstsq` residuals on the same design; canonical correlations via QR + SVD of the centered residual blocks; `scipy.stats.f.sf`, `scipy.stats.norm.sf`; no pgmpy/sklearn import), the scenarios above (seeded `np.random.default_rng`, continuous data rounded to 6 decimals, discrete columns as integer codes), the validator rules (extend the existing `rel_tol` rule so it is required for hsic/kci/gcm/pillai), regenerate `golden.json`, update `golden.rs` (`run_case` builds `Gcm::new()` / `Pillai::new()`), sync the R copy.
- [ ] **Step 4: Run** — `python -m pytest tests -q && python tests/fixtures/generate_golden.py --check && cargo test -p ci_core --test golden` → PASS.
- [ ] **Step 5: Commit** — `git commit -m "test: add GCM and Pillai golden cases"`

---

### Task 5: pgmpy parity for GCM and Pillai

**Files:**
- Modify: `tests/fixtures/check_pgmpy_parity.py`, `tests/fixtures/test_check_pgmpy_parity.py`

**Interfaces:**
- Consumes: fixture contract from Task 4.
- Produces: `CONSTRUCTORS["gcm"] = lambda m, df, p: m.GCM(data=df)`; `CONSTRUCTORS["pillai"]` → `m.PillaiTrace(data=df, estimator=LinearProbabilityModel())` where `LinearProbabilityModel` is an sklearn-compatible estimator defined in the script (subclass `sklearn.base.BaseEstimator`; `fit(X, y)` stores the OLS fit of `y` and of `y`'s one-hot columns; `predict` → OLS fitted values; `predict_proba` → fitted indicator columns in code order); discrete fixture columns cast to `category` for pillai cases; a declared Pillai tolerance constant (measured: the smallest value above the largest observed gap, e.g. `1e-6`, documented as sklearn CCA iteration tolerance); the tiny-p case compared on an absolute tolerance because pgmpy's `1 − cdf` floors near 1e-16.

- [ ] **Step 1: Failing tests**: `test_linear_probability_model_matches_ols` (predict_proba rows sum to 1; columns equal OLS on indicators); `test_pillai_cases_are_compared_with_the_declared_tolerance`; `test_gcm_case_is_strict`.
- [ ] **Step 2: Run** — `python -m pytest tests/fixtures/test_check_pgmpy_parity.py -q` → FAIL.
- [ ] **Step 3: Implement**; then measure: `PYTHONPATH= python tests/fixtures/check_pgmpy_parity.py --pgmpy-source <scratchpad>/pgmpy-opt` (snapshot of `feature/optimization` `cd3d4bee`; identical ci_tests files to `cf069b04`). If `<scratchpad>/pgmpy-opt` is missing, recreate it with `git -C /home/ankur/work/pgmpy/pgmpy archive feature/optimization | tar -x -C <scratchpad>/pgmpy-opt`.
- [ ] **Step 4: Run** — expected `failed=0`, skipped unchanged (15 + 2), divergences unchanged (2). A GCM mismatch is a bug, not a divergence.
- [ ] **Step 5: Commit** — `git commit -m "test: compare GCM and Pillai with pgmpy"`

---

### Task 6: Python binding

**Files:** `crates/ci-python/src/lib.rs`, `crates/ci-python/ci_python/__init__.py`, `crates/ci-python/ci_python/_ci_python/__init__.pyi`, `crates/ci-python/README.md`; tests `crates/ci-python/test/test_golden.py`, `crates/ci-python/test/test_api.py`

**Interfaces:** `GCM(data)`, `PillaiTrace(data)` via `ci_test_class!` with `new()` (no args); registered and exported; stub entries.

- [ ] **Step 1: Failing tests** — `test_golden.py`: add `"gcm": GCM, "pillai": PillaiTrace` to `TEST_CLASSES`; `test_api.py`: `test_gcm_and_pillai_meta` (names, data types `["continuous"]` / `["discrete", "continuous"]`, symmetric True), `test_gcm_rejects_discrete_columns` (CiError), `test_pillai_accepts_mixed_dataframe` (a pandas DataFrame with a category column and float columns, conditioning on both kinds), `test_pillai_degenerate_raises` (X determined by Z → CiError).
- [ ] **Step 2: Build + run** (scratchpad wheel; see Global Constraints) → FAIL.
- [ ] **Step 3: Implement**; README section (usage, linear residualization, difference from pgmpy's random-forest default).
- [ ] **Step 4: Run** Python tests, `ruff check` / `ruff format --check crates/ci-python`, `cargo clippy -p ci_python --all-targets -- -D warnings` → PASS.
- [ ] **Step 5: Commit** — `git commit -m "feat(python): expose GCM and PillaiTrace"`

---

### Task 7: JS binding

**Files:** `crates/ci-js/src/lib.rs`, `crates/ci-js/README.md`; tests `crates/ci-js/tests/golden.test.js`, `crates/ci-js/tests/api.test.js`

**Interfaces:** `new GCM(data, options?)`, `new PillaiTrace(data, options?)` with `EmptyConfig` (`"Record<string, never> | undefined"`).

- [ ] **Step 1: Failing tests** — golden `TEST_CLASSES` gains `gcm`, `pillai`; `api.test.js` `describe("GCM and PillaiTrace")`: meta, GCM on a discrete column throws, Pillai on a mixed columns object runs, unknown option key throws.
- [ ] **Step 2: Build + run** — `cd crates/ci-js && ~/.cargo/bin/wasm-pack build --target nodejs --out-dir pkg && npm test` → FAIL (run `npm ci` first if `node_modules` is missing).
- [ ] **Step 3: Implement**; README rows/example.
- [ ] **Step 4: Run** `npm test`, `npx eslint .`, `npx prettier --check .`, clippy (host and `--target wasm32-unknown-unknown`) → PASS; record `.wasm` size before/after.
- [ ] **Step 5: Commit** — `git commit -m "feat(js): expose GCM and PillaiTrace"`

---

### Task 8: R binding

**Files:** `crates/ci-r/src/rust/src/lib.rs`, `crates/ci-r/R/tests.R`, regenerated `crates/ci-r/R/extendr-wrappers.R`, `crates/ci-r/NAMESPACE`, `crates/ci-r/man/{gcm,pillai}.Rd`, `crates/ci-r/README.md`; tests `crates/ci-r/tests/testthat/test-golden.R`, `test-api.R`

**Interfaces:** extendr handles `GCM$new(data)`, `Pillai$new(data)` via `ci_test_handle!` (no args); R factories `gcm(data)`, `pillai(data)` with roxygen (`@param data`, `@return`, `@examples`, `@export`).

- [ ] **Step 1: Failing tests** — golden factories gain `gcm`, `pillai`; `test-api.R`: meta/decision rule for both, `gcm()` on a factor column errors, `pillai()` on a data.frame with a factor and numeric columns runs with mixed z, degenerate case errors.
- [ ] **Step 2: Run** — `conda run -n cir-dev bash -c 'export LD_LIBRARY_PATH=$CONDA_PREFIX/lib/R/lib:$CONDA_PREFIX/lib; Rscript -e "devtools::test(\"crates/ci-r\")"'` → FAIL.
- [ ] **Step 3: Implement**, then `rextendr::document("crates/ci-r")` in `cir-dev`; revert incidental roxygen-version churn in files not related to this task (DESCRIPTION `RoxygenNote`, unrelated `.Rd`).
- [ ] **Step 4: Run** `devtools::test`, lintr on changed files, `R CMD build` (< 5 MB) and `R CMD check --as-cran --no-manual` (0 errors; the 2 known WARNINGs — CRAN incoming feasibility and checkbashisms/top-level notices — are pre-existing), `sync_package_assets.py --check`, `python -m pytest tests -q` → PASS.
- [ ] **Step 5: Commit** — `git commit -m "feat(r): expose GCM and pillai"`

---

### Task 9: Quick timing and full verification

**Files:** none in the repo (scripts in `<scratchpad>/cmp5/`).

- [ ] **Step 1: Quick per-query timing** (best of 3 per query, fresh objects per pass, same queries for every engine): GCM on the 30-variable Gaussian data (n = 10 000, 50 queries, |Z| 0–4) — ci-tests vs pgmpy `GCM` (`feature/optimization` snapshot `<scratchpad>/pgmpy-opt`); Pillai on a mixed dataset (n = 2 000; 3 categorical + 3 continuous columns; 40 queries, |Z| 0–2) — ci-tests vs pgmpy `PillaiTrace` with the `LinearProbabilityModel` from Task 5 and vs pgmpy's default random forest (report both; check the linear pair agrees to the Task 5 tolerance). Reuse `<scratchpad>/cmp4/gauss10k.csv` if present; otherwise regenerate it with `<scratchpad>/cmp4/make_data.py`'s Gaussian recipe (30 variables, `np.random.default_rng(0)`, edge probability 3/29 upper-triangular, weights `U(0.5, 1.5)·±1`, unit-variance noise, n = 10 000). Generate the mixed dataset with a fixed seed in the script.
- [ ] **Step 2: Full verification**

```bash
cargo fmt --check && cargo clippy --all-targets -- -D warnings && cargo test -p ci_core
python -m pytest tests -q
python tests/fixtures/generate_golden.py --check && python crates/ci-r/tools/sync_package_assets.py --check
# Python: Task 6 Step 2 commands; JS: Task 7 Step 2; R: Task 8 Step 2
PYTHONPATH= python tests/fixtures/check_pgmpy_parity.py --pgmpy-source <scratchpad>/pgmpy-opt
```
Expected: everything passes; report the timing table, sizes, and that nothing was pushed.
