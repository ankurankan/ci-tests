# Contributing to FastCIT

Read this guide before you open a pull request.

## Set up

Install these tools:

- Rust, stable channel ([rustup](https://rustup.rs/)). The R package needs Rust 1.85 or newer.
- Git.
- Python 3.10 to 3.14, for the Python binding.
- R 4.2 or newer, for the R binding.
- Node.js (current LTS) and [wasm-pack](https://rustwasm.github.io/wasm-pack/), for the JavaScript binding.

The core crate needs only Rust.
Each binding has its own toolchain.
Run these commands to set up and to check your environment:

```bash
git clone https://github.com/pgmpy/FastCIT
cd FastCIT
rustup component add rustfmt clippy
cargo fmt --all -- --check
cargo clippy -p fastcit-core --all-targets -- -D warnings
cargo test -p fastcit-core
```

## Repository structure

```
FastCIT/
├── crates/
│   ├── ci-core/     # Core tests, Dataset, CITest trait, registry (crate fastcit-core)
│   ├── ci-python/   # Python binding (PyO3 and maturin, crate fastcit-python)
│   ├── ci-r/        # R binding (extendr, R package fastcit)
│   └── ci-js/       # JavaScript binding (wasm-pack, crate fastcit)
├── tests/           # Documentation tests and the golden fixture (tests/fixtures/)
├── docs/            # Documentation site (Sphinx and MyST), published at pgmpy.org/FastCIT
├── benchmarks/      # Benchmark scripts and results
├── devtools/        # Templates for a new test (extension_templates/)
└── .github/         # Pull request template and one workflow for each language
```

The root Cargo workspace contains `ci-core`, `ci-python` and `ci-js`.
`ci-r` is a separate package, so that R can build it outside this repository.
Each crate has a `README.md`.

The core keeps shared computation apart from the statistics of a test:

| File | Responsibility |
| --- | --- |
| `dataset.rs` | Column storage, encoding, query validation, cache lifetime |
| `correlation.rs`, `gram.rs` | Shared correlation, residual regression, Fisher transform, lazy covariance cache |
| `strata.rs` | Conditioning-set groups and their bounded cache |
| `discrete.rs` | Contingency tables and power-divergence calculations |
| `kernel.rs`, `residual.rs` | Kernel matrices and linear residuals |
| `ci_tests/power_divergence.rs` | The five discrete tests |
| `ci_tests/<name>.rs` | One file for each other test: statistics, p-values, metadata |
| `strategy.rs`, `registry.rs` | The `CITest` trait and the default test catalogue |

Put the tests of an implementation in the same file.
Put a shared helper in the module of its users.
`DataType` is an alias of `ColumnKind` for old code.

Binding code:

- Python: `_column_from_pandas` in `crates/ci-python/fastcit/__init__.py` classifies and encodes pandas columns.
- JavaScript: `crates/ci-js/src/options.rs` holds the option defaults, the allowed keys and the TypeScript option types.
- R: `R/dataset.R` builds datasets, `R/tests.R` holds the factories and queries, and `R/adapters.R` holds the `pcalg` and `htest` adapters.
- R: `R/fastcit.R` holds the package documentation. `rextendr::document()` generates `R/extendr-wrappers.R`. Do not edit it.

The copy of the core in `crates/ci-r/src/rust/ci-core` is a distribution asset, not a second implementation.
After you change the core, run `python crates/ci-r/tools/sync_package_assets.py --sync`.

## Code standards

- Run `cargo fmt --all` before you commit. The line length is 100 characters.
- Fix every Clippy lint. If you think a lint is wrong, explain it in your pull request.
- Use `Result` and `?`. Do not use `unwrap()` in library code. The workspace forbids `unsafe` code.
- Document public items with `///` comments.
- Give each function one job and each variable a clear name.
- Write tests for new behavior, and a regression test for each bug fix.
- Name tests clearly, for example `test_chi_squared_with_independent_variables`. Test the success case and the error case.

Python code uses `ruff`, R code uses `styler` and `lintr`, and JavaScript code uses `prettier` and `eslint` (see [Testing](#testing)).

Write commit messages in the [Conventional Commits](https://www.conventionalcommits.org/) format.
The type is `feat`, `fix`, `docs`, `test`, `refactor`, `perf` or `chore`.

```
<type>(<scope>): <description>

feat(core): add Student's t-test implementation
fix(python): resolve memory leak in data conversion
```

## Add a test

A test holds only its configuration.
It works on a `Dataset` that the caller passes at query time.
A new test needs an implementation of `CITest` in the core, an entry in the registry, and one small wrapper in each binding.

Follow the steps in [`devtools/extension_templates/README.md`](devtools/extension_templates/README.md).
It lists every file that a new test changes, with the rules for the examples and the documentation page.
Start from [`_ci_test.rs`](devtools/extension_templates/_ci_test.rs).
It is a complete test, and `cargo test -p fastcit-core` compiles it.
For a new member of the power-divergence family, add a declaration to `crates/ci-core/src/ci_tests/power_divergence.rs` instead.

Obey these rules of the design:

- Implement `test_impl` and `meta` of `CITest` (`crates/ci-core/src/strategy.rs`).
  The provided `test` method validates the query `(x, y, z)` and then calls `test_impl`.
  Your code can assume that the query is valid.
- `TestMeta` holds the decision rule.
  Use `IndependenceRule::PValueGe`, or `PValueLt` for an equivalence (TOST) test such as `pearson_equivalence.rs`.
  `is_independent` has a default implementation.
- `default_tests()` in `crates/ci-core/src/registry.rs` is the single source of truth.
  Callers use it to list the tests and to build one by its `meta().name`.
- Return a `CIError`.
  Never let a panic reach a binding.
- Keep shared numerical code in `discrete.rs` or `correlation.rs`.
- The R adapters read the decision rule from the test metadata, so they need no list of tests.

Obey these rules for the tests of a new test:

- Add Rust tests in a `#[cfg(test)] mod tests` block in the implementation file.
- Add binding tests in `crates/ci-python/test/`, `crates/ci-r/tests/testthat/` and `crates/ci-js/tests/`.
- Use known inputs and known outputs.
- Cover edge cases: one category, zero variance, NaN and sparse strata.
- If scipy or another reference gives the same test, add cases to the golden fixture (see [Testing](#testing)).

Obey these rules for the examples:

- Each language makes its own random data, so start each example with a comment line that says this.
- In a Python example, use `>>> print(result.dof)` for a `None` field.
  Doctest shows no output for a bare `None`.
- If numpy or R changes its random stream, run the examples again and update the written output.

## Testing

The crates use different toolchains, so no single command runs all tests.
Run the suite of each language that you changed.
CI runs one workflow for each language.

### Golden fixture

`tests/fixtures/golden.json` holds reference values that `tests/fixtures/generate_golden.py` computes with scipy and other references.
Each case has the test name, its parameters, the columns with their kinds, `X`, `Y`, `Z`, and the expected `statistic`, `p_value`, `dof` and `effect_size`.
Every language suite checks that its binding gives these values, within `1e-7` or the `rel_tol` of the case.
The fixture is the numeric parity gate between the languages.
Each suite runs every case and checks that every supported test has a case:

- Rust: `crates/ci-core/tests/golden.rs`
- Python: `crates/ci-python/test/test_golden.py`
- R: `crates/ci-r/tests/testthat/test-golden.R` (it reads a byte-identical copy in the R package)
- JavaScript: `crates/ci-js/tests/golden.test.js`

When you change a statistic or add a test, regenerate the fixture and check it:

```bash
python -m pip install -r tests/fixtures/requirements.txt
python tests/fixtures/generate_golden.py
python tests/fixtures/generate_golden.py --check
python crates/ci-r/tools/sync_package_assets.py --sync
python crates/ci-r/tools/sync_package_assets.py --check
pytest tests
# Optional: compare with a local pgmpy checkout
python tests/fixtures/check_pgmpy_parity.py --pgmpy-source /path/to/pgmpy
```

### Rust

```bash
cargo test -p fastcit-core                    # includes the golden test
cargo test -p fastcit-core test_chi_squared   # one test
cargo test -p fastcit-core -- --nocapture     # show println! output
# Compare an example with its output comments (CI does this for every example)
cargo run -q -p fastcit-core --example fisher_z | python3 crates/ci-core/examples/check_output.py crates/ci-core/examples/fisher_z.rs
```

### Python

The tests use [pytest](https://pytest.org/).
Build the binding with [maturin](https://www.maturin.rs/) first.
On a Python newer than the installed PyO3 supports, set `PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1`.

```bash
cd crates/ci-python
pip install maturin numpy pandas pandas-stubs pytest mypy ruff
maturin develop
pytest              # tests, golden test and the examples (*.pycon) as doctests
mypy test/
ruff format --check .
ruff check .
```

### R

The tests use [testthat](https://testthat.r-lib.org/) with [rextendr](https://extendr.github.io/rextendr/).
Run these commands in an R session in `crates/ci-r/`:

```r
rextendr::document()   # compile the Rust code and regenerate the wrappers
devtools::test()       # all tests, including test-golden.R
lintr::lint_package()  # CI fails on any lint
```

CI also checks the style of the `R/` files (not `R/extendr-wrappers.R`) with `styler`, and builds and checks the source package.

Caution: `rextendr::document()` and `devtools::load_all()` compile the Rust core without optimization.
This is correct for tests but not for benchmarks.
For benchmarks, install a release build with `NOT_CRAN=true R CMD INSTALL crates/ci-r`.
The install uses the release profile when the `DEBUG` environment variable is not set.
The install generates `src/Makevars`.
Do not commit it.

### JavaScript

The tests use [vitest](https://vitest.dev/).
Build the WASM package first.

```bash
wasm-pack build crates/ci-js --target nodejs   # writes crates/ci-js/pkg
cd crates/ci-js
npm ci
npm test                # includes golden.test.js
npx prettier --check .
npx eslint .
```

### Documentation

Build the documentation site with warnings as errors (Python 3.13 or newer):

```bash
pip install -r docs/requirements.txt -c docs/constraints.txt
sphinx-build -W -b html docs site
pytest tests/test_docs_site.py
```

## Pull requests

1. Create a branch from `main`: `git checkout -b feature/your-feature-name`.
2. Commit your changes.
3. Run the checks for each language that you changed (see [Testing](#testing)).
4. For a core change, also run `cargo fmt --all`, the Clippy command and `cargo test -p fastcit-core`.
5. Push the branch and open a pull request to `main` on GitHub.
6. Fill in the template: the change, the related issues, the incompatible changes and the checklist.
7. Request a review from at least one maintainer.

All CI checks must pass.
Answer review comments with new commits.
Rebase on `main` to resolve conflicts.
A pull request needs one approval.
The maintainers squash merge: the commits become one commit on `main`.
Delete your branch after the merge.
