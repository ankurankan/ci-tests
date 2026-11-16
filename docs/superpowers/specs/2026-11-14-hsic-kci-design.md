# HSIC and KCI for ci-tests — design

Date: 2026-11-14 (updated 2026-11-16 after the builder check) · Status: awaiting approval

## Intent

ci-tests is a Rust core (`ci_core`) of conditional-independence (CI) tests translated
from pgmpy, with Python (PyO3, `ci_python`), R (extendr, `cir`) and JS/WASM (`ci_js`)
bindings. It currently covers 8 of pgmpy's 17 CI test classes. The owner wants the
remaining pgmpy tests ported **one at a time**; this document covers the first batch:
**HSIC** (unconditional kernel independence test) and **KCI** (kernel conditional
independence test).

Why: parity with pgmpy's test catalog, so ci-tests can serve as a fast engine for
constraint-based causal discovery (the earlier benchmark showed 2–50× speedups for the
existing tests inside pgmpy's PC). The owner chose how kernels are specified
(Approaches, below); everything else marked "my call" is the designer's decision and
open to correction.

Reference implementation: pgmpy `dev` at commit `cf069b04`,
files `pgmpy/ci_tests/hsic.py` and `pgmpy/ci_tests/kci.py` (a snapshot is in the
session scratchpad; the same commit is reachable from the sibling `../pgmpy` checkout
via `upstream/dev`).

## Goals

- `HSIC` and `KCI` in `ci_core`, exposed with identical features in Python, R and JS.
- Numerically match pgmpy (gamma null, all built-in kernel configurations) within the
  fixture tolerance described below.
- Golden fixture cases from an independent numpy/scipy reference, checked by all four
  harnesses (Rust, Python, R, JS), plus pgmpy parity via `check_pgmpy_parity.py`.
- HSIC substantially faster than pgmpy; KCI benchmarked against pgmpy and reported.
  pgmpy baseline on this machine (OpenBLAS, 14 cores, single query, X ⊥ Y | Z):
  KCI 0.27 s @ n=300, 0.61 s @ n=1000, 5.6 s @ n=2000; HSIC 0.007 s / 0.07 s / 0.21 s.
  A single-threaded faer prototype of the KCI steps took 1.14 s @ n=1000 and 11.8 s @
  n=2000, so **single-query KCI is expected to be ~2× slower than pgmpy** at n ≥ 1000
  (both are dominated by the same dense eigendecompositions; timings are noisy on this
  busy machine). The owner accepted this: the gain for causal discovery comes from
  running queries in parallel, since the bindings release the GIL.

## Non-goals

- Arbitrary sklearn `Kernel` objects (approach 2 below; can be layered on later).
- Approximate / low-rank kernels (random features, Nyström) for large n.
- Caching Z-dependent matrices across queries.
- The other seven missing pgmpy tests (Pillai, Hotelling–Lawley, Roy, Wilks,
  GeneralizedCov, GCM, IndependenceMatch) and arbitrary-λ PowerDivergence.
- A "supports conditioning" flag on `TestMeta` (HSIC simply rejects a non-empty Z).
- Multithreading inside a single query (owner's decision: single-threaded in every
  binding for now; no rayon, no `parallel` feature).

## Anti-goals

- Results that differ from pgmpy beyond the divergences listed in this document.
- OS entropy / `getrandom` in any build (a release test asserts JS has no `getrandom`).
- A Rust panic escaping into Python, R or JS.

## Constraints

- Minimal dependency tree is an explicit project value:
  `tests/test_release_configuration.py::test_rust_distribution_dependency_tree_is_minimal`
  pins `statrs` features; a past commit was "build: trim unused statistical dependencies".
- R package: Rust MSRV **1.81** is asserted in `crates/ci-r/src/rust/Cargo.toml`,
  `crates/ci-r/DESCRIPTION` (`SystemRequirements`), `.github/workflows/r.yml`
  ("Install Rust MSRV") and `test_r_msrv_is_advertised_preflighted_and_exercised`.
- R package vendors all crates into the committed `crates/ci-r/src/rust/vendor.tar.xz`
  (1.07 MB today); `test_r_vendor_archive_matches_the_locked_crate_set_and_declares_licenses`
  requires the archive to equal the R lockfile's registry crate set.
  `crates/ci-r/src/rust/ci-core` is a synced copy of the core
  (`crates/ci-r/tools/sync_package_assets.py --check`).
- WASM target: single-threaded.
- **CRAN is a target** (owner's decision): the built R source package
  (`R CMD build` output) must stay under CRAN's 5 MB limit.
- **Nothing is pushed** to GitHub (no branch, no PR) until the owner asks.
- Fixture comparisons today are **absolute 1e-7** in all four harnesses
  (`crates/ci-core/tests/golden.rs`, `crates/ci-python/test/test_golden.py`,
  `crates/ci-js/tests/golden.test.js`, `crates/ci-r/tests/testthat/test-golden.R`) and in
  `generate_golden.py --check`.
- R is not installed on the development machine: R changes are verified only by the
  `r.yml` GitHub workflow, which runs on `pull_request` (it regenerates extendr wrappers
  with `rextendr::document()` and runs `devtools::test` / `check_built`).
- KCI is O(n²) memory and O(n³) time, exactly as in pgmpy.
- R is verified locally on Linux only (see Verification); macOS/Windows R builds run
  only in CI on a PR, i.e. at the end, when the owner asks for one.

## Approaches

### Kernel specification (owner's decision)

1. **Built-in kernels in the Rust core — chosen.** RBF (fixed length scale, or the
   `heuristic` / `median` bandwidth rules) and linear, per-column overrides as in
   pgmpy's dict form. Identical across Python, R, JS. Covers every kernel pgmpy's own
   HSIC/KCI tests use (`RBF`, `DotProduct`). Cannot accept arbitrary sklearn kernels.
2. Option 1 plus a Python-only path that evaluates an arbitrary sklearn kernel in Python
   and passes the n×n matrix to Rust. Full drop-in for pgmpy's `kernel=`; deferred — it
   can be added on top of 1 without rework.
3. Approximate kernels — dropped: different numbers from pgmpy.

### Dense linear algebra (my call: faer)

Measured on this machine (n×n symmetric eigendecomposition / matmul):

| | eigh n=1000 | eigh n=2000 | matmul n=1000 | R vendor archive (xz) | MSRV |
|---|---|---|---|---|---|
| faer 0.24 (sequential) | 0.23 s | 1.18 s | 0.09 s | ~3.7 MB filtered / 5.8 MB unfiltered | 1.85 (via `generativity` 1.2) |
| nalgebra 0.33 | 1.63 s | 18.98 s | 0.10 s | ~1.7 MB | ≤ 1.81 |
| hand-written in ci_core | ≥ nalgebra | | | 1.07 MB (unchanged) | 1.81 |

faer builds for `wasm32-unknown-unknown` (+0.37 MB .wasm for eigh + Cholesky).
Chosen: **faer 0.24**, `default-features = false`, features `["std", "linalg"]`
(no rayon). nalgebra/hand-written would make KCI several times slower than pgmpy.

## Design

### Math (exact port of pgmpy `cf069b04`)

Shared:

- Each queried column is standardized: `(v − mean) / sd` with `ddof = 1`. pgmpy
  standardizes all columns once at construction; per-query standardization of the same
  columns is numerically identical.
- RBF kernel: `k(a, b) = exp(−‖a − b‖² / (2ℓ²))` (sklearn `RBF(ℓ)`; sklearn computes
  `cdist(a/ℓ, b/ℓ, "sqeuclidean")` then `exp(−½·d)` — follow that order for parity).
- Linear kernel: `k(a, b) = a·b`. sklearn's `DotProduct(σ₀)` adds `σ₀²`, which cancels
  in every quantity used below (centered matrices, and `tr(K)/n − μ` in the HSIC gamma
  mean), so `Linear` matches `DotProduct()` for any `σ₀`.
- Centering: `K̃ = K − colmean − colmean[:, None] + mean(colmean)`.
- Gamma p-value from moments: if `var ≤ 0` or `mean ≤ 0` → `1.0`; else
  `Gamma(shape = mean²/var, scale = var/mean).sf(stat)`.
- Median bandwidth: Euclidean pairwise distances of the (standardized) input rows,
  drop zeros, numpy median (mean of the two middle values when even), divide by √2;
  `1.0` if no non-zero distance.

HSIC (`X ⊥ Y`, Z must be empty):

- Default per-column RBF length scale: `heuristic` → 0.8 if n < 200, 0.5 if n < 1200,
  else 0.3; `median` → median rule on that single column.
- `Kx`, `Ky` (uncentered), `K̃x`, `K̃y`; `stat = Σ K̃x ∘ K̃y`;
  `effect_size = stat / sqrt(⟨K̃x, K̃x⟩ ⟨K̃y, K̃y⟩)`.
- Gamma null (default): if n < 6 → p = 1.0. Else with `P = K̃x ∘ K̃y`,
  `n_pairs = n(n−1)`:
  `off = (⟨P, P⟩ − Σ diag(P)²) / 36`;
  `factor = 72 (n−4)(n−5) / (n_pairs (n−2)(n−3))`;
  `var = factor · off / n_pairs`;
  `μx = (ΣKx − tr Kx) / n_pairs`, likewise `μy`;
  `mean = (tr Kx / n − μx)(tr Ky / n − μy) / n`;
  `p = gamma_sf(stat / n; mean = n·mean, var = n²·var)`.
- Permutation null: `count = #{b : ⟨K̃x, K̃y[π_b, π_b]⟩ ≥ stat}` over `n_permutations`
  permutations; `p = (1 + count) / (1 + n_permutations)`. (No n < 6 special case.)

KCI (`X ⊥ Y | Z`):

- Empty Z → exactly the HSIC computation with **HSIC's** default kernels/bandwidths and
  the gamma null (pgmpy's `super()._compute_result`).
- Otherwise: `x_aug = [X, 0.5·Z]` (columns side by side), `y = [Y]`, `z = Z`.
- Default kernel length scales: `heuristic` → `w · sqrt(|Z|)` for all three kernels,
  `w` = 1.2 if n < 200, 0.7 if n < 1200, else 0.4; `median` → median rule on each of
  `x_aug`, `y`, `z` separately.
- `K̃x, K̃y, K̃z` centered; `Rz = ε (K̃z + εI)⁻¹`; `KxR = Rz K̃x Rz`, `KyR = Rz K̃y Rz`.
- `stat = ⟨KxR, KyR⟩`; `effect_size = stat / sqrt(⟨KxR, KxR⟩ ⟨KyR, KyR⟩)`.
- Null: eigendecompose `½(KxR + KxRᵀ)` and `½(KyR + KyRᵀ)`; keep eigenpairs with
  `w > max(w) · 1e−5`; `Vx = vecs · sqrt(w)` (kept only); `U = (Vx Vxᵀ) ∘ (Vy Vyᵀ)`;
  `p = gamma_sf(stat; mean = tr U, var = 2 ⟨U, U⟩)`.

Kernel-choice semantics (match pgmpy, including its quirks):

| Choice | HSIC (and KCI with empty Z) | KCI with non-empty Z |
|---|---|---|
| Default | default RBF per column | default RBF for x_aug, y, z |
| One kernel for all | that kernel for X and Y | that kernel for x_aug, y **and z** |
| Per-column map | listed columns use their kernel; others default | X/Y looked up (default if absent); **z always default RBF**; map entries for Z columns are ignored |

### Core API (`ci_core`)

- New public module (my call: `ci_core::kernel`):
  - `enum Kernel { Rbf { length_scale: f64 }, Linear }`
  - `enum Bandwidth { Heuristic, Median }`
  - `enum KernelChoice { Default, All(Kernel), PerColumn(BTreeMap<String, Kernel>) }`
    — keyed by **column name** (my call: core tests are not bound to a dataset; names
    stay valid for any dataset, and bindings validate names at construction).
- `enum NullDistribution { Gamma, Permutation { n_permutations: usize, seed: u64 } }`
- `pub struct Hsic { kernel, bandwidth, null_dist }` and
  `pub struct Kci { kernel, bandwidth, epsilon }` with `new()` = pgmpy defaults
  (Default kernel, Heuristic, Gamma; `epsilon = 1e-3`). Rust type names are the
  builder's call (clippy `upper_case_acronyms` favours `Hsic`/`Kci`); binding-facing
  names are `HSIC` / `KCI`.
- `fn validate(&self) -> Result<(), CiError>` on both, called by bindings at
  construction (so bad config raises immediately, like pgmpy's `ValueError`) and again
  in `test_impl`. Rules: RBF `length_scale` finite and > 0; `epsilon` finite and > 0;
  `n_permutations ≥ 1`.
- `TestMeta`: `hsic` — symmetric, Continuous, `PValueGe`; `kci` — **not** symmetric
  (X is augmented with Z), Continuous, `PValueGe`.
- `CiResult`: `statistic`, `p_value`, `effect_size`; `dof = None`.
- Errors: discrete X/Y/Z → `WrongColumnKind` (via `Dataset::continuous`); HSIC with
  non-empty z → `InvalidQuery` (pgmpy silently ignores Z — declared divergence);
  zero-variance X/Y/Z column → `DegenerateData` (pgmpy yields NaN — declared
  divergence); n < 2 → `DegenerateData`. Any faer failure → `Numeric`, never a panic.
- Registry: add `hsic` and `kci` with defaults; registry tests and every "eight tests"
  mention become ten.

### Permutation RNG (my call)

In-crate, fully specified, version-stable generator so p-values are reproducible across
Python/R/JS and across dependency upgrades, and so the fixture reference can reproduce
them exactly. No `rand`, no `getrandom`.

- SplitMix64: `state += 0x9E3779B97F4A7C15; z = state;
  z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9; z = (z ^ (z >> 27)) * 0x94D049BB133111EB;
  return z ^ (z >> 31)` (wrapping u64 arithmetic), initial `state = seed`.
- Unbiased bounded draw in `[0, m)`: `t = (2⁶⁴ − m) mod m`; draw `r` until `r ≥ t`;
  return `r mod m`.
- Each permutation: start from identity `[0, n)`, Fisher–Yates
  `for i in (1..n).rev() { j = bounded(i + 1); swap(i, j) }`; the generator stream
  continues across permutations.
- Default `seed = 0` (deterministic). Divergence from pgmpy (numpy `Generator`,
  default fresh entropy) is declared; permutation cases are skipped in pgmpy parity.

### Bindings

Python (`ci_python`):

- `HSIC(data, kernel=None, bandwidth="heuristic", null_dist="gamma", n_permutations=100, seed=0)`
- `KCI(data, kernel=None, bandwidth="heuristic", epsilon=1e-3)`
- Kernel values: new frozen classes `RBF(length_scale)` and `Linear()`.
  `kernel` accepts `None`, one kernel, or `dict[str, RBF | Linear]`; dict keys must be
  columns of the dataset (else `ValueError`, like pgmpy). Names mirror pgmpy except
  `seed` (pgmpy: `rng`, which also accepts numpy Generators — we take an int only).
- Update `ci_python/__init__.py` exports and the hand-maintained stub
  `ci_python/_ci_python/__init__.pyi`.

R (`cir`):

- `hsic(data, kernel = NULL, bandwidth = "heuristic", null_dist = "gamma", n_permutations = 100L, seed = 0)`
- `kci(data, kernel = NULL, bandwidth = "heuristic", epsilon = 1e-3)`
- Kernel constructors `rbf_kernel(length_scale)` and `linear_kernel()` (S3 class
  `cir_kernel`); per-column = named list of `cir_kernel`. Flatten to plain vectors
  (names / types / length scales) before crossing into Rust. `seed`: non-negative whole
  number ≤ 2⁵³.
- Hand-write extendr wrappers, roxygen docs, `man/*.Rd` and `NAMESPACE` entries
  following the generated pattern (R is unavailable locally; CI regenerates/validates).

JS (`ci_js`):

- `new HSIC(data, { kernel?, kernels?, bandwidth?, nullDist?, nPermutations?, seed? })`
- `new KCI(data, { kernel?, kernels?, bandwidth?, epsilon? })`
- `KernelSpec = { type: "rbf", lengthScale: number } | { type: "linear" }`;
  `kernel` (all columns) and `kernels` (`Record<columnName, KernelSpec>`) are mutually
  exclusive (my call: a single overloaded key would be ambiguous for a column named
  `type`). `seed`: safe non-negative integer. Unknown keys rejected (existing `Config`
  trait). TypeScript custom sections for the new option types.

### Fixtures and parity

- `tests/fixtures/generate_golden.py`: independent numpy/scipy reference (no pgmpy, no
  sklearn) implementing the math above, plus a Python port of the RNG for permutation
  cases. Update `EXPECTED_CASE_COUNT` / `EXPECTED_COUNTS` and `validate_cases` param
  rules.
- Params JSON shape (each harness maps it to its binding's form):
  `kernel`: `null` | `{"type": "rbf", "length_scale": ℓ}` | `{"type": "linear"}` |
  `{"columns": {name: kernel}}`; plus `bandwidth`, and `null_dist` / `n_permutations`
  / `seed` (HSIC) or `epsilon` (KCI).
- Tolerance (my call): add an optional per-case `rel_tol`; a value passes when
  `|actual − expected| ≤ max(1e-300, rel_tol · |expected|)` — purely relative, so
  tiny p-values are genuinely checked (an absolute 1e-7 floor would accept 0.0 for a
  1e-60 p-value). Needed because HSIC/KCI statistics are sums over n² entries (pgmpy's
  docstring example: 5468.71), where absolute 1e-7 would demand bit-level
  summation-order agreement. Start at `1e-9` for HSIC/KCI cases; cases without
  `rel_tol` keep today's pure absolute 1e-7. All four harnesses and the generator's
  `--check` honour it. (The builder check found statrs 0.18's gamma upper tail agrees
  with scipy to ≥ 7 digits for tails between 1e-61 and 1e-127.)
- Scenario coverage (exact data is the builder's call): HSIC independent / linear
  dependence / nonlinear dependence; n in each heuristic band (< 200, 200–1199, ≥ 1200
  — HSIC is O(n²) so n≈1500 is fine); median bandwidth; explicit RBF for all; linear
  for all; per-column mix; n < 6 (p = 1.0); a very small p-value (≈1e-60) to pin
  gamma upper-tail accuracy; two permutation cases. KCI: |Z| = 1 and 2; independent and
  dependent; heuristic bands < 200 and 200–1199; median; explicit RBF for all (applies
  to Z); linear for all; per-column map containing a Z entry (ignored); empty Z
  (HSIC fallback); a swapped X/Y case showing asymmetry. Keep KCI n ≤ ~400 so debug
  `cargo test` stays fast.
- Fixture size budget (my call): ≤ 250 KB added to `golden.json` (144 KB today; it is
  copied into the R package). Store continuous fixture data rounded to 6 decimal places
  (the reference computes on the rounded values, so this costs no accuracy). Drop the
  HSIC n ≥ 1200 band from the fixture (~90 KB per case) and cover that band's length
  scale (0.3 / 0.4·√|Z|) with Rust unit tests instead.
- `tests/fixtures/check_pgmpy_parity.py`: factories mapping fixture params to pgmpy
  `HSIC` / `KCI` with sklearn `RBF(ℓ)` / `DotProduct()`; declared skips for permutation
  cases; declared divergences for any zero-variance/HSIC-with-Z cases if included.
  Bump `tests/fixtures/requirements-pgmpy.txt` from `8a221e91` (predates HSIC/KCI) to
  `cf069b04` (earlier parity run against `cf069b04`: 65 compared, only the 2 known
  pearson-equivalence dof divergences).

### Dependencies and packaging

- Add `faer = { version = "0.24", default-features = false, features = ["std", "linalg"] }`
  to the root `[workspace.dependencies]` and the R workspace
  (`crates/ci-r/src/rust/Cargo.toml`); extend
  `test_rust_distribution_dependency_tree_is_minimal` to pin it.
- R MSRV 1.81 → **1.85** (my call). faer itself needs 1.84, but its dependency
  `generativity` 1.2.1 is edition 2024 and needs 1.85; bumping to 1.85 is simpler and
  less fragile than pinning `generativity` 1.1.x in the R lockfile. Update all five
  places: the four listed under Constraints plus `crates/ci-r/README.md`.
- Regenerate `vendor.tar.xz` filtered to crates actually compiled on the supported R
  platforms (Linux, macOS, Windows): `windows-sys`, `winapi-util`, `same-file`,
  `walkdir` arrive only through faer → gemm-common → `sysctl`, which is macOS-only, so
  they are unused on every platform. Measured: ~3.7 MB filtered vs 5.8 MB unfiltered
  vs 1.07 MB today. Filtering is **mandatory** (CRAN target). The vendor test must then
  allow a documented exclusion list, and an offline `cargo build --locked` against the
  filtered vendor dir must still succeed (e.g. `cargo-vendor-filterer` stubs). Do this
  first: build offline on Linux, and `cargo check --offline --locked` for the macOS
  (`aarch64-apple-darwin`, `x86_64-apple-darwin`) and Windows (`x86_64-pc-windows-gnu`)
  targets locally (adding rustup targets as needed). **If the filtered bundle cannot be
  made to build offline, stop and return to the owner** before going further.
- Third-party notices for the new vendored crates follow the existing policy in
  `crates/ci-r/THIRD-PARTY-NOTICES` (builder's call on scope; note statrs is not listed
  there today).

### Documentation

README "Available Tests" table and quick starts; `ci_core` crate docs (`lib.rs` table,
`ci_tests/mod.rs`, `registry.rs`); binding READMEs; Python stub; R roxygen/man; JS
TypeScript sections. Mention the O(n²)/O(n³) cost and the pgmpy divergences.

### Verification

- `cargo fmt --check`; `cargo clippy --all-targets -- -D warnings`; `cargo test -p ci_core`.
- Python (`maturin` build + pytest), JS (`wasm-pack` + vitest + eslint/prettier), repo
  `tests/` (release configuration, R assets), `generate_golden.py --check`,
  `sync_package_assets.py --check`, `check_pgmpy_parity.py` against `cf069b04`.
- R on Linux: locally, in a separate conda environment with R, devtools, rextendr and
  testthat (my call; the existing `pgmpy` environment is not touched).
- Built R source tarball size < 5 MB, checked locally with `R CMD build`.
- R on macOS/Windows: via the `r.yml` workflow on a pull request, only once the owner
  asks for one; until then, the local cross-target `cargo check` above stands in.
- Benchmark single-query HSIC and KCI vs pgmpy at n = 300 / 1000 / 2000, plus a PC
  run with parallel queries, and report. No threading is added regardless of the result
  (owner's decision); report the numbers so it can be revisited.

## Left to the builder

- Module/file layout inside `ci_core`, helper structure, error wording.
- Efficient kernel evaluation and summation strategy (e.g. streaming the HSIC gamma
  sums in O(n) memory), and how `Rz` is formed (Cholesky solve vs eigh) — as long as
  results stay within tolerance of the reference.
- Exact fixture datasets and generators.
- Whether to guard against very large n (no guard required; pgmpy has none).
- Work on a local feature branch off `main`; commit locally as the plan dictates;
  push / PR only when the owner asks.

## Risks

- Eigenvalues near the `1e-5 · max` cutoff could be kept by LAPACK but dropped by faer
  (or vice versa), shifting KCI p-values beyond tolerance. Fixtures should avoid
  borderline spectra; the parity checker reports any case that trips.
- `statrs` gamma upper-tail accuracy for tiny p-values — verify against scipy; fall back
  to a log-space or own continued-fraction implementation if needed.
- Filtered vendoring for R must still build offline on all three platforms.
- Fixture growth inflates the R package (fixture is synced into `tests/testthat`).
