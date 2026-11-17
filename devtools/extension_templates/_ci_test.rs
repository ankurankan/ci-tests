//! TODO: One-line summary of the test, and its data type, in one sentence.
//!
//! TODO: The method, in two to five sentences. Name every symbol. Give the statistic, the
//! p-value, the degrees of freedom and the effect size as formulas, for example
//! `T = r * sqrt(dof / (1 - r^2))` and `p = 2 * P(t_dof > |T|)`.
//!
//! TODO: One sentence for each known difference from pgmpy or from a reference.
//!
//! References: TODO author (year), title.

// ---------------------------------------------------------------------------------------------
// HOW TO USE THIS TEMPLATE
//
// This file is a complete, working test. `cargo test -p fastcit-core` compiles it, so it stays
// correct when the `CITest` trait changes. The placeholder test is a Student-t test of the
// partial correlation. Replace its math with your own.
//
// Core steps (this file):
//   1. Copy this file to `crates/ci-core/src/ci_tests/<key>.rs`. Use a snake_case key.
//   2. Rename `ExampleTest` and the string "example_test" (the key). Resolve every TODO.
//   3. Remove all comments that start with `// TEMPLATE:` and this block.
//   4. Declare the module in `crates/ci-core/src/ci_tests/mod.rs`:
//          pub mod <key>;
//          pub use <key>::<YourTest>;
//   5. Register the test in `crates/ci-core/src/registry.rs`:
//          - add `<YourTest>` to the `use crate::ci_tests::{...}` list,
//          - add `Box::new(<YourTest>::new()),` to `default_tests()`,
//          - add the key to `EXPECTED_NAMES` and raise the array length,
//          - update the count and the table in the crate docs (`crates/ci-core/src/lib.rs`).
//      A test with options needs a default configuration in the registry. Name that default in
//      the doc comment of `make_default`.
//
// Then follow `devtools/extension_templates/README.md` for the bindings, the golden fixture, the
// examples and the docs page.
// ---------------------------------------------------------------------------------------------

// TEMPLATE: Import only what you use. Clippy runs with `-D warnings`.
use statrs::distribution::{ContinuousCDF, StudentsT};

use crate::correlation::partial_correlation;
use crate::dataset::Dataset;
use crate::error::CIError;
use crate::strategy::{CIResult, CITest, DataType, IndependenceRule, TestMeta};

// TEMPLATE: Give each default a named constant. The registry and the bindings use the same value.
/// Default for [`ExampleTest::min_rows`].
const DEFAULT_MIN_ROWS: usize = 10;

/// TODO: One-line summary, the same as in the module doc.
///
/// TODO: One or two sentences on what the test checks and when to use it.
///
/// # Parameters
///
/// - `min_rows`: The smallest number of rows the test accepts. The default is 10.
///
/// # Example
///
/// ```ignore
/// use fastcit_core::ci_tests::ExampleTest;
/// use fastcit_core::dataset::{ColumnKind, Dataset};
/// use fastcit_core::strategy::CITest;
///
/// // TEMPLATE: Make this a real doctest. Build a small dataset, run the test, assert on it.
/// let data = Dataset::from_columns(vec![
///     ("x".into(), ColumnKind::Continuous, vec![1.0, 2.0, 3.0, 4.0]),
///     ("y".into(), ColumnKind::Continuous, vec![1.1, 1.9, 3.2, 3.9]),
/// ])
/// .unwrap();
/// let result = ExampleTest::new().test(&data, 0, 1, &[]).unwrap();
/// assert!(result.p_value < 1.0);
/// ```
// TEMPLATE: The struct holds options only. It never holds data. Derive `Copy` only if every field
// is `Copy`. Derive `Eq` only if no field is a float.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ExampleTest {
    /// The smallest number of rows the test accepts.
    pub min_rows: usize,
}

impl ExampleTest {
    // TEMPLATE: A test with no options has `new()` only, and derives `Default` (see `FisherZ`).
    // A test with options has `new()` with the default options, and `Default` calls it.
    /// Construct the test with the default options.
    #[must_use]
    pub fn new() -> Self {
        Self {
            min_rows: DEFAULT_MIN_ROWS,
        }
    }
}

impl Default for ExampleTest {
    fn default() -> Self {
        Self::new()
    }
}

impl CITest for ExampleTest {
    // TEMPLATE: Implement `test_impl`, not `test`. The provided `test` has already checked that
    // the indices are in range, that x != y, and that z has no repeats and excludes x and y.
    // The short names x, y and z are the repo convention, so the allow below is expected.
    #[allow(
        clippy::many_single_char_names,
        reason = "x, y, z are the standard conditional-independence variable names from the contract"
    )]
    fn test_impl(
        &self,
        data: &Dataset,
        x: usize,
        y: usize,
        z: &[usize],
    ) -> Result<CIResult, CIError> {
        // Step 1: Check the column kinds.
        // TEMPLATE: A continuous-only test returns `CIError::WrongColumnKind`. `data.continuous`
        // does this. A discrete test uses `data.discrete`. A mixed test accepts both kinds.
        data.continuous(x)?;
        data.continuous(y)?;
        for &c in z {
            data.continuous(c)?;
        }

        // Step 2: Check the sample size.
        // TEMPLATE: Return `CIError::DegenerateData` for data the test cannot use. Never panic.
        // Never return NaN as a result.
        let n = data.n_rows();
        if n < self.min_rows {
            return Err(CIError::DegenerateData(format!(
                "{n} rows is fewer than min_rows = {}",
                self.min_rows
            )));
        }

        // Step 3: Compute the statistic.
        // TEMPLATE: Reuse the shared helpers. `correlation.rs` has the partial correlation,
        // `residual.rs` has the OLS residuals, `discrete.rs` has the contingency tables.
        // Put new numerical code that two tests can share in one of these files.
        let (r, dof) = partial_correlation(data, x, y, z)?;
        if r * r >= 1.0 {
            return Err(CIError::DegenerateData(
                "correlation is +1 or -1, so the statistic is undefined".to_string(),
            ));
        }
        #[allow(clippy::cast_precision_loss)]
        let dof_f = dof as f64;
        let statistic = r * (dof_f / (1.0 - r * r)).sqrt();

        // Step 4: Compute the p-value.
        // TEMPLATE: Map a failed distribution setup to `CIError::Numeric`.
        let dist = StudentsT::new(0.0, 1.0, dof_f)
            .map_err(|e| CIError::Numeric(format!("Student's t distribution: {e}")))?;
        let p_value = 2.0 * dist.sf(statistic.abs());

        // Step 5: Return the result.
        // TEMPLATE: Use `None` for a field the test does not define, for example `dof: None`.
        Ok(CIResult {
            statistic: Some(statistic),
            p_value,
            dof: Some(dof),
            effect_size: Some(r.abs()),
        })
    }

    // TEMPLATE: Check the options here. Bindings call `validate` when they build the test, so a
    // bad option fails early. The provided `test` also calls it on every query.
    fn validate(&self, _data: &Dataset) -> Result<(), CIError> {
        if self.min_rows == 0 {
            return Err(CIError::InvalidConfig(
                "min_rows must be at least 1".to_string(),
            ));
        }
        Ok(())
    }

    fn meta(&self) -> TestMeta {
        TestMeta {
            // TODO: The stable key. Bindings, docs and the golden fixture use this name.
            name: "example_test",
            // TODO: `Continuous`, `Discrete`, or both for a mixed-data test.
            data_types: &[DataType::Continuous],
            // TODO: `true` if swapping x and y never changes the result.
            symmetric: true,
            // TODO: `PValueGe` (independent when p >= alpha) for a normal test.
            // `PValueLt` (independent when p < alpha) only for an equivalence test.
            rule: IndependenceRule::PValueGe,
        }
    }
}

// TEMPLATE: Tests live in this file, in this module. Test against a closed form or a reference
// value, not against the code under test. Cover each error the test can return.
#[cfg(test)]
mod tests {
    use super::*;
    use crate::dataset::ColumnKind;

    /// A seeded generator, so every run gives the same data.
    fn lcg(n: usize, seed: u64) -> Vec<f64> {
        let mut s = seed;
        (0..n)
            .map(|_| {
                s = s
                    .wrapping_mul(6_364_136_223_846_793_005)
                    .wrapping_add(1_442_695_040_888_963_407);
                #[allow(clippy::cast_precision_loss)]
                let v = (s >> 11) as f64 / (1u64 << 53) as f64;
                v - 0.5
            })
            .collect()
    }

    fn continuous(cols: Vec<(&str, Vec<f64>)>) -> Dataset {
        Dataset::from_columns(
            cols.into_iter()
                .map(|(name, v)| (name.to_string(), ColumnKind::Continuous, v))
                .collect(),
        )
        .unwrap()
    }

    #[test]
    #[allow(clippy::many_single_char_names)] // The closed form uses the textbook symbols.
    fn matches_closed_form() {
        // X depends on Y. The closed form is the Pearson r with t = r * sqrt((n - 2) / (1 - r^2)).
        let n = 40;
        let y = lcg(n, 1);
        let noise = lcg(n, 2);
        let x: Vec<f64> = y.iter().zip(&noise).map(|(a, b)| a + 2.0 * b).collect();
        let data = continuous(vec![("x", x.clone()), ("y", y.clone())]);

        let result = ExampleTest::new().test(&data, 0, 1, &[]).unwrap();

        #[allow(clippy::cast_precision_loss)]
        let nf = n as f64;
        let (mx, my) = (x.iter().sum::<f64>() / nf, y.iter().sum::<f64>() / nf);
        let sxy: f64 = x.iter().zip(&y).map(|(a, b)| (a - mx) * (b - my)).sum();
        let sxx: f64 = x.iter().map(|a| (a - mx).powi(2)).sum();
        let syy: f64 = y.iter().map(|b| (b - my).powi(2)).sum();
        let r = sxy / (sxx * syy).sqrt();
        let t = r * ((nf - 2.0) / (1.0 - r * r)).sqrt();
        let p = 2.0 * StudentsT::new(0.0, 1.0, nf - 2.0).unwrap().sf(t.abs());

        assert!((result.statistic.unwrap() - t).abs() < 1e-10);
        assert!((result.p_value - p).abs() < 1e-10);
        assert!((result.effect_size.unwrap() - r.abs()).abs() < 1e-10);
        assert_eq!(result.dof, Some(n - 2));
    }

    #[test]
    fn symmetric_in_x_and_y() {
        // TEMPLATE: Keep this test only if `meta().symmetric` is true.
        let data = continuous(vec![
            ("x", lcg(30, 3)),
            ("y", lcg(30, 4)),
            ("z", lcg(30, 5)),
        ]);
        let a = ExampleTest::new().test(&data, 0, 1, &[2]).unwrap();
        let b = ExampleTest::new().test(&data, 1, 0, &[2]).unwrap();
        assert!((a.p_value - b.p_value).abs() < 1e-12);
    }

    #[test]
    fn meta_describes_the_test() {
        let meta = ExampleTest::new().meta();
        assert_eq!(meta.name, "example_test");
        assert_eq!(meta.data_types, &[DataType::Continuous]);
        assert!(meta.symmetric);
        assert_eq!(meta.rule, IndependenceRule::PValueGe);
    }

    #[test]
    fn discrete_column_is_wrong_kind() {
        let data = Dataset::from_columns(vec![
            ("x".into(), ColumnKind::Continuous, lcg(20, 6)),
            ("y".into(), ColumnKind::Discrete, [0.0, 1.0].repeat(10)),
        ])
        .unwrap();
        assert!(matches!(
            ExampleTest::new().test(&data, 0, 1, &[]),
            Err(CIError::WrongColumnKind(_))
        ));
    }

    #[test]
    fn too_few_rows_is_degenerate() {
        let data = continuous(vec![("x", lcg(5, 7)), ("y", lcg(5, 8))]);
        assert!(matches!(
            ExampleTest::new().test(&data, 0, 1, &[]),
            Err(CIError::DegenerateData(_))
        ));
    }

    #[test]
    fn constant_column_is_degenerate() {
        let data = continuous(vec![("x", vec![0.5; 20]), ("y", lcg(20, 9))]);
        assert!(matches!(
            ExampleTest::new().test(&data, 0, 1, &[]),
            Err(CIError::DegenerateData(_))
        ));
    }

    #[test]
    fn zero_min_rows_is_invalid_config() {
        let data = continuous(vec![("x", lcg(20, 10)), ("y", lcg(20, 11))]);
        assert!(matches!(
            ExampleTest { min_rows: 0 }.test(&data, 0, 1, &[]),
            Err(CIError::InvalidConfig(_))
        ));
    }

    #[test]
    fn malformed_query_is_rejected() {
        let data = continuous(vec![("x", lcg(20, 12)), ("y", lcg(20, 13))]);
        assert!(matches!(
            ExampleTest::new().test(&data, 0, 0, &[]),
            Err(CIError::InvalidQuery(_))
        ));
    }
}
