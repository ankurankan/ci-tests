# Contributing to CI Testing Library

This document provides guidelines and instructions for contributing to the CI Testing library.

## Table of Contents

- [Development Setup](#development-setup)
- [Repository Structure](#repository-structure)
- [Coding Standards](#coding-standards)
- [Adding a New CI Test](#adding-a-new-ci-test)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)

## Development Setup

### Prerequisites

- **Rust** (stable, latest version): [Install Rust](https://rustup.rs/)
- **Git**: For version control
- **Python 3.10** (for Python bindings development)
- **R 4.2+** (for R bindings development)
- **Node.js 16+** (for JavaScript bindings development)

### Initial Setup

1. **Clone the repository**:
```bash
   git clone https://github.com/pgmpy/FastCIT
   cd FastCIT
```

2. **Build the core crate** (each binding has its own toolchain; see [Testing](#testing)):
```bash
   cargo build -p fastcit-core
```

3. **Run tests to verify setup**:
```bash
   cargo test -p fastcit-core
```

4. **Install development tools**:
```bash
   # Rustfmt (code formatter)
   rustup component add rustfmt

   # Clippy (linter)
   rustup component add clippy
```

### Verify Your Setup

Run these commands to ensure everything works:
```bash
# Check formatting
cargo fmt --all -- --check

# Run linter on the core crate
cargo clippy -p fastcit-core --all-targets -- -D warnings

# Run the core crate's tests (includes the golden parity test)
cargo test -p fastcit-core
```

If all commands complete successfully, your environment is ready!

## Repository Structure
```
FastCIT/
├── crates/                 # Rust workspace
│   ├── ci-core/           # Core CI test implementations, Dataset, CITest trait, registry
│   ├── ci-python/         # Python bindings (PyO3 + maturin)
│   ├── ci-r/              # R bindings (extendr); R package name is `fastcit`
│   └── ci-js/             # JavaScript/WASM bindings (wasm-pack)
├── tests/fixtures/        # Shared golden.json + generate_golden.py (cross-language parity)
├── docs/                  # Documentation site (Sphinx, MyST pages), published at pgmpy.org/FastCIT
└── .github/               # CI/CD workflows (one per language)
```

See individual `README.md` files in each directory for more details.

Within the core, keep shared computation separate from a test's statistical interpretation:

| File | Responsibility |
| --- | --- |
| `dataset.rs` | Column storage, encoding, query validation, and cache lifetime |
| `correlation.rs` | Shared correlation, residual regression, and Fisher transform |
| `gram.rs` | Lazy covariance cache and linear algebra used by correlation |
| `strata.rs` | Conditioning-set grouping and its bounded cache |
| `discrete.rs` | Contingency tables and power-divergence calculations |
| `ci_tests/power_divergence.rs` | The five named discrete tests, configuration, and result assembly |
| `ci_tests/{pearson_correlation,fisher_z,pearson_equivalence}.rs` | Test-specific statistics, p-values, and metadata |
| `strategy.rs`, `registry.rs` | Shared test contract and default test catalogue |

Keep implementation-specific tests alongside the behavior they exercise. Shared helpers
belong with their consumers' common domain, not inside a sibling test implementation.
`ColumnKind` describes column types throughout the core; `DataType` remains a compatibility
alias for existing users.

In the bindings, pandas classification and encoding live together in Python's
`_column_from_pandas`; JavaScript option defaults, allowed keys, and TypeScript option
declarations live in `crates/ci-js/src/options.rs`. R's maintained code is split into
`R/dataset.R` (conversion and dataset construction), `R/tests.R` (factories and queries),
and `R/adapters.R` (`pcalg` and `htest` adapters). `R/fastcit.R` holds package documentation;
`R/extendr-wrappers.R` is generated.

The core copy under `crates/ci-r/src/rust/ci-core` is a distribution asset, not a second
implementation. After changing the canonical core, synchronize it with
`python crates/ci-r/tools/sync_package_assets.py --sync`.

## Coding Standards

### Rust Code Style

We follow the official Rust style guide, enforced by `rustfmt`:

- **Always run `cargo fmt --all` before committing**
- Use 4 spaces for indentation (automatic with rustfmt)
- Maximum line length: 100 characters
- Use trailing commas in multi-line constructs

### Linting

We use Clippy with strict settings:

- **All Clippy warnings must be fixed** before merging
- Run `cargo clippy -p fastcit-core --all-targets -- -D warnings` (and the relevant binding crate
  for binding changes)
- If you believe a warning is a false positive, discuss in your PR

### Code Quality

- **Write tests** for all new functionality
- **Document public APIs** with doc comments (`///`)
- **Keep functions focused**: One function should do one thing well
- **Avoid `unwrap()` in library code**: Use proper error handling with `Result` and `?`
- **Use meaningful variable names**: Prefer clarity over brevity

### Git Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) format:
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Adding or updating tests
- `refactor`: Code restructuring without behavior change
- `perf`: Performance improvements
- `chore`: Maintenance tasks

**Examples**:
```
feat(core): add Student's t-test implementation

fix(python): resolve memory leak in data conversion

docs(readme): update installation instructions

test(core): add property tests for chi-squared test
```

## Adding a New CI Test

The library is **data-bound**: a test holds only its own configuration and operates on a
`Dataset` passed to it at query time. Adding a test means implementing the `CITest` trait in
the core, registering it, and adding a thin wrapper in each binding. Unlike the old codegen
path, the bindings are now hand-written (one small wrapper per language), so a new test is a
handful of mechanical additions.

**Start from the template.** Copy [`devtools/extension_templates/_ci_test.rs`](devtools/extension_templates/_ci_test.rs)
for the core test. The compiler checks it in `cargo test -p fastcit-core`, so it follows the current `CITest` trait.
[`devtools/extension_templates/README.md`](devtools/extension_templates/README.md) lists every file a new test touches,
and [`_docs_page.md`](devtools/extension_templates/_docs_page.md) is the docs page template. The sections below explain
the same steps in more detail.

### 1. Create the Core Implementation

Create a new file in `crates/ci-core/src/ci_tests/`:
```bash
crates/ci-core/src/ci_tests/students_t.rs
```

For another member of the existing power-divergence family, add a declaration to
`ci_tests/power_divergence.rs` instead of creating another wrapper file. Keep shared
numerical work in `discrete.rs` or `correlation.rs` and test-specific interpretation in
`ci_tests/`.

### 2. Implement the `CITest` Trait

Your test struct holds **only** its configuration and implements the `CITest` trait defined in
`crates/ci-core/src/strategy.rs`. You implement the required `test_impl` method; the provided
`test` method validates the `(x, y, z)` query and delegates to it, so implementations may
assume a well-formed query. Per-test config is constructor fields, the decision rule lives in
`TestMeta`, and `is_independent` has a default impl (no per-test branching at the call site):

```rust
use crate::dataset::{ColumnKind, Dataset};
use crate::error::CiError;
use crate::strategy::{CITest, CiResult, IndependenceRule, TestMeta};

pub struct StudentsT { /* config fields only */ }

impl CITest for StudentsT {
    fn test_impl(&self, data: &Dataset, x: usize, y: usize, z: &[usize]) -> Result<CiResult, CiError> {
        // ... return CiResult { statistic, p_value, dof, effect_size }
    }

    fn meta(&self) -> TestMeta {
        TestMeta {
            name: "students_t",
            data_types: &[ColumnKind::Continuous],
            symmetric: true,
            rule: IndependenceRule::PValueGe,   // or PValueLt for an equivalence/TOST test
        }
    }
}
```

See existing tests (e.g., `power_divergence.rs`, or `pearson_equivalence.rs` for the inverted rule)
as examples. Return `CiError` rather than panicking; never let a panic escape into a binding.

### 3. Export and Register the Test

- Add your test to `crates/ci-core/src/ci_tests/mod.rs` so it is publicly accessible:

  ```rust
  pub mod students_t;
  pub use students_t::StudentsT;
  ```

- Register it in `crates/ci-core/src/registry.rs` (`default_tests()`), the single source of
  truth that lets callers enumerate tests and construct one by its stable `meta().name`. Add
  the name to the registry's test assertions too.

### 4. Add the Binding Wrappers

Each binding has one small wrapper per test; add yours next to the existing ones:

- **Python** — add a `ci_test_class!(...)` invocation in `crates/ci-python/src/lib.rs` (mapping
  the constructor kwargs onto your config) and register the generated class in the `#[pymodule]`
  at the bottom of that file. Re-export it from `crates/ci-python/fastcit/__init__.py` and add
  it to the `.pyi` stub.
- **R** — add a factory function in `crates/ci-r/R/tests.R` (following `chi_squared()` /
  `pearson_equivalence()`), and export the extendr handle in the Rust glue
  (`crates/ci-r/src/rust/src/lib.rs`). Run `rextendr::document()` to regenerate wrappers
  and documentation. Adapters derive the decision rule from the native test metadata;
  they do not need a separate list of inverted-rule tests.
- **JavaScript** — add a `ci_test_class!(...)` invocation in `crates/ci-js/src/lib.rs` (with a
  config from `crates/ci-js/src/options.rs`). If new options are needed, define their
  defaults, allowed keys, and TypeScript declaration together in that module.

### 5. Add Tests

Add test cases for each language:

- **Rust**: In a `#[cfg(test)] mod tests { }` block in your implementation file
- **Python**: In [`crates/ci-python/test`](crates/ci-python/test).
- **R**: In `crates/ci-r/tests/testthat/`
- **JavaScript**: In [`crates/ci-js/tests`](crates/ci-js/tests).

Test with known inputs and expected outputs, and cover edge cases (single category,
zero-variance, NaN, sparse strata). If your test maps to a scipy/standard reference, add rows
for it to the shared golden fixture (see [Testing](#testing)) so every language checks it.

### 6. Update Documentation

- Add doc comments to your test struct and methods
- Add the test to the "Available Tests" table in `README.md`
- Add one example per language (`crates/ci-python/examples/<key>.py`, `crates/ci-r/inst/examples/tests/<key>.R`,
  `crates/ci-js/examples/<key>.js`, `crates/ci-core/examples/<key>.rs`)
- Add the page `docs/tests/<key>.md` (copy the layout of `docs/tests/chi_squared.md`), a row in
  `docs/_includes/test-table.md` and an entry in the toctree of `docs/tests/index.md`
- Add the key to the `TESTS` dict in `tests/test_docs_site.py`
- Raise the example count (12) in `crates/ci-python/test/test_examples.py`,
  `crates/ci-r/tests/testthat/test-examples.R` and `crates/ci-js/tests/examples.test.js`
- If the example's expected p-value is not `> 0.05`, add its key to the `case` table in the "Run examples" step of
  `.github/workflows/rust.yml`
- Build the site with warnings as errors:
  `pip install -r docs/requirements.txt -c docs/constraints.txt` (Python 3.13 or later), then
  `sphinx-build -W -b html docs site`

## Testing

Because each crate uses a different toolchain, there is no single workspace-wide test command;
run each language's suite with its own tooling, as below.

### Shared golden fixture (cross-language parity gate)

The file `tests/fixtures/golden.json` (at the repository root) holds reference values generated
from scipy / standard references by `tests/fixtures/generate_golden.py` — for each case: the
test name, its params (`yates` / `delta_threshold`), the columns (with kinds), `X` / `Y` / `Z`,
and the expected `statistic` / `p_value` / `dof` / `effect_size`. **Every** language test suite
asserts its binding reproduces these values (within `1e-7`), so it is the cross-language numeric
parity gate. R reads a byte-identical package-local copy so a built source archive remains
self-contained:

- Rust: `crates/ci-core/tests/golden.rs`
- Python: `crates/ci-python/test/test_golden.py`
- R: `crates/ci-r/tests/testthat/test-golden.R`
- JavaScript: `crates/ci-js/tests/golden.test.js`

Consumers execute every supplied case and check that every supported test is represented.
The expected catalogue size and per-test distribution are checked only by fixture tooling,
so adding reference cases does not require updating a count in four languages.

If you change a statistic or add a test, install the pinned independent-generator dependencies,
regenerate the fixture, and verify that its committed bytes are current:

```bash
python -m pip install -r tests/fixtures/requirements.txt
python tests/fixtures/generate_golden.py
python tests/fixtures/generate_golden.py --check
python crates/ci-r/tools/sync_package_assets.py --sync
python crates/ci-r/tools/sync_package_assets.py --check
python tests/fixtures/check_pgmpy_parity.py --pgmpy-source /path/to/pgmpy
```

The final command is an optional comparison against a local pgmpy checkout; it does not
participate in fixture generation. Pearson correlation reports `dof = n - |Z| - 2`, while
Fisher-Z and Pearson equivalence report no degrees of freedom.

### Rust Tests
```bash
# Run the core crate's tests (includes the golden parity test)
cargo test -p fastcit-core

# Run a specific test
cargo test -p fastcit-core test_chi_squared

# Run with output (see println! statements)
cargo test -p fastcit-core -- --nocapture
```

### Python Tests

Python tests use [pytest](https://pytest.org/) and require the bindings to be built first
via [maturin](https://www.maturin.rs/):

```bash
cd crates/ci-python

# Install build tool and build the bindings in-place
pip install maturin
maturin develop

# Run tests (includes test_golden.py)
pytest test/

# Type-check the test suite
mypy test/
```

The CI pipeline also checks formatting and linting:
```bash
ruff format .
ruff check .
```

### R Tests

R tests use [testthat](https://testthat.r-lib.org/) via the
[rextendr](https://extendr.github.io/rextendr/) integration:

```r
# From an R session in crates/ci-r/
rextendr::document()  # Recompile the Rust code and regenerate wrappers
devtools::test()      # Run all tests (includes test-golden.R)
```

> **Benchmarking warning:** `rextendr::document()` and `devtools::load_all()`
> compile the Rust core **without optimizations** (debug profile) — fine for
> tests, useless for benchmarks. To benchmark, install a release build:
> `NOT_CRAN=true R CMD INSTALL crates/ci-r` (the `configure` script selects
> `--release` whenever the `DEBUG` env var is unset) and `library(fastcit)`.
> `src/Makevars` is generated by `tools/config.R` at install time and must not
> be committed.

The CI pipeline also checks style and linting:
```r
styler::style_pkg()
lintr::lint_package()
```

### JavaScript Tests

JavaScript tests use [vitest](https://vitest.dev/) and require the WASM package to be built
first with [wasm-pack](https://rustwasm.github.io/wasm-pack/):

```bash
# Build the WASM package into crates/ci-js/pkg
wasm-pack build crates/ci-js --target nodejs

# From crates/ci-js/tests
npm ci
npm test    # vitest, includes golden.test.js
```

### Test Organisation

- **Unit tests**: Inline in each source file, inside `#[cfg(test)] mod tests { }`
- **Golden parity tests**: one per language, with R reading its synchronized package copy
- **Python integration tests**: [`crates/ci-python/test`](crates/ci-python/test)
- **R tests**: `crates/ci-r/tests/testthat/`
- **JavaScript tests**: [`crates/ci-js/tests`](crates/ci-js/tests)


### Writing Tests

- Use descriptive test names: `test_chi_squared_with_independent_variables`
- Test both success and error cases
- Add regression tests for bugs you fix

## Pull Request Process

### Before Opening a PR

1. **Create a feature branch** from `main`:
```bash
   git checkout -b feature/your-feature-name
```

2. **Make your changes** and commit with clear messages

3. **Ensure all checks pass locally** (run the suites for the languages you touched — see
   [Testing](#testing); for a core change):
```bash
   cargo fmt --all
   cargo clippy -p fastcit-core --all-targets -- -D warnings
   cargo test -p fastcit-core
```

4. **Push your branch**:
```bash
   git push origin feature/your-feature-name
```

### Opening the PR

1. Go to GitHub and create a Pull Request from your branch to `main`

2. **Fill out the PR template** (auto-generated):
   - Describe what the PR does
   - Link related issues
   - List breaking changes (if any)
   - Checklist: tests added, docs updated

3. **Request review** from at least one team member

### After Opening

- **CI must pass**: GitHub Actions will run all checks automatically (separate workflows for Rust, Python, R, and JS)
- **Address review comments**: Make changes and push new commits
- **Keep PR updated**: Rebase on `main` if needed to resolve conflicts

### Merging

- PRs require at least one approval from a team member
- All CI checks must pass (green checkmarks)
- We use **squash merging**: Multiple commits become one clean commit on `main`
- Delete your feature branch after merging


## Additional Resources

- [Rust Book](https://doc.rust-lang.org/book/) - Learn Rust
- [PyO3 Guide](https://pyo3.rs/) - Python bindings
- [extendr Guide](https://extendr.github.io/) - R bindings
- [wasm-pack](https://rustwasm.github.io/wasm-pack/) - JavaScript/WASM bindings
