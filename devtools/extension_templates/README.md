# Extension templates

Use these files to add a conditional independence test to FastCIT.
`CONTRIBUTING.md` explains the design.
This page lists every place that a new test touches.

| File | Use |
|---|---|
| [`_ci_test.rs`](_ci_test.rs) | The Rust test, with its registry steps and unit tests. |
| [`_docs_page.md`](_docs_page.md) | The docs page `docs/tests/<key>.md`. |

`cargo test -p fastcit-core` compiles `_ci_test.rs` (see `extension_template` in `crates/ci-core/src/lib.rs`).
The file is not in the registry and not in the public API.
Change the template in the same pull request that changes the `CITest` trait.

In the steps below, `<key>` is the snake_case key, for example `gcm`.
`<Class>` is the Rust struct, for example `Gcm`.
`<PyClass>` is the Python and JavaScript class, for example `GCM`.
The R function is `<key>()`.
Copy the files of an existing test with the same options as your test.
`gcm` has no options. `chi_squared` has one option, `yates`.

## Steps

1. **Core.** Copy `_ci_test.rs` to `crates/ci-core/src/ci_tests/<key>.rs`.
   Follow the steps in its header: module, `pub use`, registry.
2. **Python.** In `crates/ci-python/src/lib.rs`, add a `ci_test_class!` call.
   Add `m.add_class::<Py<Class>>()?;` to the `#[pymodule]`.
   Export `<PyClass>` in `crates/ci-python/fastcit/__init__.py` (import and `__all__`).
   Add a class to `crates/ci-python/fastcit/_fastcit/__init__.pyi`.
3. **R.** In `crates/ci-r/src/rust/src/lib.rs`, add a `ci_test_handle!` call and an `impl <PyClass>;` line.
   In `crates/ci-r/R/tests.R`, add the `<key>()` function with roxygen docs.
   Run `rextendr::document()` to update `NAMESPACE`, `man/` and `R/extendr-wrappers.R`.
4. **JavaScript.** In `crates/ci-js/src/lib.rs`, add a `ci_test_class!` call.
   A test with options needs a config in `crates/ci-js/src/options.rs`.
   Define the defaults, the allowed keys and the TypeScript type together.
5. **R sync.** Run `python3 crates/ci-r/tools/sync_package_assets.py --sync`.
   It copies `crates/ci-core` into the R package. Commit the result.
   The tool copies only `Cargo.toml`, `README.md` and `src/`. It does not copy these templates.
6. **Golden fixture.** Add a reference function and scenarios in `tests/fixtures/generate_golden.py`.
   Add the key to the `params` validation there, then regenerate `tests/fixtures/golden.json`.
   Copy it to `crates/ci-r/tests/testthat/fixtures/golden.json` (the sync tool does this).
   Add the key to the constructor maps in `crates/ci-core/tests/golden.rs` (also its required-tests list),
   `crates/ci-python/test/test_golden.py`, `crates/ci-r/tests/testthat/test-golden.R` and `crates/ci-js/tests/golden.test.js`.
7. **Binding tests.** Add a test of `meta()` and of one error in `crates/ci-python/test/test_api.py`,
   `crates/ci-r/tests/testthat/test-api.R` and `crates/ci-js/tests/api.test.js`.
8. **Examples.** Copy the four `gcm` examples and change the class.
   Each example shows the four result fields and their output.
   - `crates/ci-python/examples/<key>.pycon`: a doctest transcript.
   - `crates/ci-r/inst/examples/tests/<key>.R`: the output in `#> ` comments under each `print()` line.
   - `crates/ci-js/examples/<key>.js`: the output in `// ` comments under each `console.log()` line.
   - `crates/ci-core/examples/<key>.rs`: the output in `// ` comments under each `println!` line.

   Run each example and replace the copied output with its output.
   - Python: `pytest --doctest-continue-on-failure crates/ci-python/examples/<key>.pycon`
     shows every real output as "Got".
   - R: `Rscript crates/ci-r/inst/examples/tests/<key>.R` runs the file.
   - JavaScript: first run `wasm-pack build --target nodejs --out-dir pkg` in `crates/ci-js`.
     The examples load `fastcit` as a package, so copy `pkg/` into a scratch `node_modules`:
     `mkdir -p "$TMPDIR/nm" && cp -r crates/ci-js/pkg "$TMPDIR/nm/fastcit" && NODE_PATH="$TMPDIR/nm" node crates/ci-js/examples/<key>.js`.
     On a mismatch, `npm test` in `crates/ci-js` prints "shows X, but prints Y".
   - Rust: `cargo run -p fastcit-core --example <key>` runs the example.

   Write numbers with 4 significant digits and integers exact.
   Keep at least one decimal place in a number of 1000 or more (write `2629.3`, not `2629`).
   A number without a decimal point is compared as exact text.
   The example tests check each shown output to the written precision.
   Do not put other comments directly under a print line.
   Raise the example count in `crates/ci-python/test/test_examples.py`,
   `crates/ci-r/tests/testthat/test-examples.R` and `crates/ci-js/tests/examples.test.js`.
9. **Docs.** Copy `_docs_page.md` to `docs/tests/<key>.md` and resolve every TODO.
   Add a row to `docs/_includes/test-table.md` and the key to the toctree in `docs/tests/index.md`.
   Update the count in the first sentence of `docs/tests/index.md` and in `crates/ci-core/README.md`.
   Add the key to the `TESTS` dict in `tests/test_docs_site.py`.
   Add a row to the "Available Tests" table in `README.md`.

## Check

```bash
cargo fmt --check
cargo clippy -p fastcit-core --all-targets -- -D warnings
cargo test -p fastcit-core
cargo run -q -p fastcit-core --example <key> | python3 crates/ci-core/examples/check_output.py crates/ci-core/examples/<key>.rs
python3 crates/ci-r/tools/sync_package_assets.py --check
pytest tests/test_docs_site.py
```

Then run the Python, R and JavaScript test suites (see `CONTRIBUTING.md`, "Testing").
