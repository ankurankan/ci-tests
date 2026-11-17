//! Named power-divergence tests, their configuration, and result conversion.
//!
//! All five tests use the contingency-table engine in [`crate::discrete`].

use statrs::distribution::{ChiSquared as ChiSquaredDist, ContinuousCDF};

use crate::dataset::Dataset;
use crate::discrete::{
    power_divergence_conditional, power_divergence_unconditional, DiscreteOutcome,
};
use crate::error::CIError;
use crate::strategy::{CIResult, CITest, DataType, IndependenceRule, TestMeta};

// Each named test differs only in its stable name and power-divergence λ.
macro_rules! power_divergence_test {
    ($(#[$doc:meta])* $test:ident, $name:literal, $lambda:expr) => {
        $(#[$doc])*
        #[derive(Debug, Clone, Copy, PartialEq, Eq)]
        pub struct $test {
            /// Whether to apply Yates' continuity correction on 2×2 (sub-)tables.
            pub yates: bool,
        }

        impl $test {
            /// Construct the test with Yates' continuity correction enabled.
            #[must_use]
            pub fn new() -> Self {
                Self { yates: true }
            }
        }

        impl Default for $test {
            fn default() -> Self {
                Self::new()
            }
        }

        impl CITest for $test {
            fn test_impl(
                &self,
                data: &Dataset,
                x: usize,
                y: usize,
                z: &[usize],
            ) -> Result<CIResult, CIError> {
                run_power_divergence(data, x, y, z, $lambda, self.yates)
            }

            fn meta(&self) -> TestMeta {
                discrete_meta($name)
            }
        }
    };
}

power_divergence_test! {
    /// Pearson chi-squared test for discrete data (power divergence with λ = 1).
    ///
    /// When `yates` is set, Yates' continuity correction is applied on 2×2
    /// (sub-)tables, matching `scipy.stats.chi2_contingency(correction=True)` and
    /// pgmpy. Cramér's V is reported as the effect size.
    ChiSquared, "chi_squared", 1.0
}

power_divergence_test! {
    /// Log-likelihood ratio (G-test) for discrete data (power divergence with λ = 0).
    ///
    /// The per-cell statistic is `2 · Σ O·ln(O/E)`. When `yates` is set, Yates'
    /// continuity correction is applied on 2×2 (sub-)tables. Cramér's V is reported
    /// as the effect size.
    LogLikelihood, "log_likelihood", 0.0
}

power_divergence_test! {
    /// Cressie-Read power-divergence test for discrete data (λ = 2/3), the
    /// recommended compromise between Pearson and the likelihood-ratio statistics.
    ///
    /// When `yates` is set, Yates' continuity correction is applied on 2×2
    /// (sub-)tables. Cramér's V is reported as the effect size.
    CressieRead, "cressie_read", 2.0 / 3.0
}

power_divergence_test! {
    /// Freeman-Tukey power-divergence test for discrete data (λ = −1/2).
    ///
    /// When `yates` is set, Yates' continuity correction is applied on 2×2
    /// (sub-)tables. Cramér's V is reported as the effect size.
    FreemanTukey, "freeman_tukey", -0.5
}

power_divergence_test! {
    /// Modified log-likelihood (Neyman) power-divergence test for discrete data
    /// (λ = −1). The per-cell statistic is `2 · Σ E·ln(E/O)`; a structural zero
    /// (`O = 0` with `E > 0`) drives the statistic to `+∞` and hence the p-value to
    /// `0`.
    ///
    /// When `yates` is set, Yates' continuity correction is applied on 2×2
    /// (sub-)tables. Cramér's V is reported as the effect size.
    ModifiedLikelihood, "modified_likelihood", -1.0
}

/// Cramér's V = sqrt(stat / (n * (min(kx, ky) - 1))). Returns `None` when the
/// smaller cardinality is < 2 (V undefined) or there are no rows.
///
/// The statistic is mathematically non-negative, but `powf` rounding in the
/// power-divergence back-end can make it a tiny *negative* value on tables where
/// observed == expected (e.g. a balanced independent table under Cressie-Read),
/// which would turn the `sqrt` into `NaN`. Clamp the radicand at 0 so the effect
/// size is a clean `0.0` there.
#[allow(clippy::cast_precision_loss)]
fn cramers_v(statistic: f64, n: usize, kx: usize, ky: usize) -> Option<f64> {
    let k = kx.min(ky);
    if k < 2 || n == 0 {
        return None;
    }
    Some((statistic.max(0.0) / (n as f64 * (k as f64 - 1.0))).sqrt())
}

/// Survival function `P(χ²_dof > statistic)`, with the degenerate and infinite
/// cases handled exactly: `dof == 0 ⇒ 1.0`, `statistic == +∞ ⇒ 0.0`.
fn chi_squared_sf(statistic: f64, dof: usize) -> Result<f64, CIError> {
    if dof == 0 {
        return Ok(1.0);
    }
    if statistic.is_infinite() {
        return Ok(0.0);
    }
    #[allow(clippy::cast_precision_loss)]
    let p = ChiSquaredDist::new(dof as f64)
        .map_err(|e| CIError::Numeric(format!("chi-squared distribution: {e}")))?
        .sf(statistic);
    Ok(p)
}

/// Run a power-divergence test with parameter `lambda` and Yates flag `yates`,
/// returning the full [`CIResult`] (statistic, p-value via the chi-squared
/// survival function, dof, Cramér's V effect size).
///
/// # Errors
///
/// Propagates [`CIError`] from reading the columns or constructing the
/// chi-squared distribution.
#[allow(
    clippy::many_single_char_names,
    reason = "x, y, z are the standard conditional-independence variable names from the contract"
)]
fn run_power_divergence(
    data: &Dataset,
    x: usize,
    y: usize,
    z: &[usize],
    lambda: f64,
    yates: bool,
) -> Result<CIResult, CIError> {
    let (x_codes, kx) = data.discrete(x)?;
    let (y_codes, ky) = data.discrete(y)?;

    let DiscreteOutcome { statistic, dof } = if z.is_empty() {
        power_divergence_unconditional(x_codes, y_codes, kx, ky, lambda, yates)
    } else {
        let partition = data.strata_partition(z)?;
        power_divergence_conditional(x_codes, y_codes, kx, ky, &partition, lambda, yates)
    };

    let p_value = chi_squared_sf(statistic, dof)?;
    let effect_size = cramers_v(statistic, data.n_rows(), kx, ky);

    Ok(CIResult {
        statistic: Some(statistic),
        p_value,
        dof: Some(dof),
        effect_size,
    })
}

/// Build the [`TestMeta`] common to every discrete power-divergence test: the
/// given stable `name`, `[Discrete]`, symmetric, and the standard
/// null-of-independence [`IndependenceRule::PValueGe`].
fn discrete_meta(name: &'static str) -> TestMeta {
    TestMeta {
        name,
        data_types: &[DataType::Discrete],
        symmetric: true,
        rule: IndependenceRule::PValueGe,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::dataset::ColumnKind;

    fn discrete_dataset(cols: Vec<(&str, Vec<f64>)>) -> Dataset {
        Dataset::from_columns(
            cols.into_iter()
                .map(|(name, values)| (name.to_string(), ColumnKind::Discrete, values))
                .collect(),
        )
        .unwrap()
    }

    fn assert_discrete_contract(test: &dyn CITest, expected_name: &str) {
        let data = discrete_dataset(vec![
            ("x", vec![1., 1., 2., 2., 1., 1., 2., 2.]),
            ("y", vec![1., 2., 1., 2., 1., 2., 1., 2.]),
        ]);
        let result = test.test(&data, 0, 1, &[]).unwrap();
        let Some(statistic) = result.statistic else {
            panic!("{expected_name}: independent data must produce a statistic");
        };
        assert!(
            statistic.abs() < 1e-9,
            "{expected_name}: expected a near-zero statistic for independent data, got {statistic}"
        );
        assert_eq!(
            result.dof,
            Some(1),
            "{expected_name}: expected one degree of freedom for independent data"
        );
        assert!(
            result.p_value > 0.99,
            "{expected_name}: expected a p-value above 0.99 for independent data, got {}",
            result.p_value
        );

        let meta = test.meta();
        assert_eq!(
            meta.name, expected_name,
            "{expected_name}: metadata must retain the family name"
        );
        assert_eq!(
            meta.data_types,
            &[DataType::Discrete],
            "{expected_name}: metadata must accept discrete data"
        );
        assert!(
            meta.symmetric,
            "{expected_name}: metadata must declare a symmetric test"
        );
        assert_eq!(
            meta.rule,
            IndependenceRule::PValueGe,
            "{expected_name}: metadata must use the p-value-greater-or-equal rule"
        );
    }

    #[test]
    fn family_members_share_contract() {
        for (name, test) in [
            (
                "chi_squared",
                &ChiSquared::new() as &dyn crate::strategy::CITest,
            ),
            ("log_likelihood", &LogLikelihood::new()),
            ("cressie_read", &CressieRead::new()),
            ("freeman_tukey", &FreemanTukey::new()),
            ("modified_likelihood", &ModifiedLikelihood::new()),
        ] {
            assert_discrete_contract(test, name);
        }
    }

    #[test]
    fn contract_failures_identify_the_family() {
        struct WrongResult;

        impl CITest for WrongResult {
            fn test_impl(
                &self,
                _data: &Dataset,
                _x: usize,
                _y: usize,
                _z: &[usize],
            ) -> Result<CIResult, CIError> {
                Ok(CIResult {
                    statistic: Some(1.0),
                    p_value: 1.0,
                    dof: Some(1),
                    effect_size: None,
                })
            }

            fn meta(&self) -> TestMeta {
                super::discrete_meta("wrong_result")
            }
        }

        let panic = std::panic::catch_unwind(|| {
            assert_discrete_contract(&WrongResult, "wrong_result");
        })
        .expect_err("the intentionally invalid result must violate the contract");
        let message = panic
            .downcast_ref::<String>()
            .map(String::as_str)
            .or_else(|| panic.downcast_ref::<&str>().copied())
            .expect("assertion panics include a message");
        assert!(message.contains("wrong_result"), "{message}");
    }

    mod chi_squared {
        use super::discrete_dataset as ds;
        use super::*;
        use crate::dataset::ColumnKind;

        #[test]
        fn unconditional_dependent_with_yates() {
            // [[4,0],[0,4]]: Yates makes stat = 4 * (1.5^2 / 2) = 4.5.
            let data = ds(vec![
                ("x", vec![1., 1., 1., 1., 2., 2., 2., 2.]),
                ("y", vec![1., 1., 1., 1., 2., 2., 2., 2.]),
            ]);
            let r = ChiSquared::new().test(&data, 0, 1, &[]).unwrap();
            assert!(
                (r.statistic.unwrap() - 4.5).abs() < 1e-9,
                "got {:?}",
                r.statistic
            );
            assert_eq!(r.dof, Some(1));
        }

        #[test]
        fn yates_off_changes_statistic() {
            // Same [[4,0],[0,4]] without Yates -> full chi-square = 8.
            let data = ds(vec![
                ("x", vec![1., 1., 1., 1., 2., 2., 2., 2.]),
                ("y", vec![1., 1., 1., 1., 2., 2., 2., 2.]),
            ]);
            let r = ChiSquared { yates: false }.test(&data, 0, 1, &[]).unwrap();
            assert!(
                (r.statistic.unwrap() - 8.0).abs() < 1e-9,
                "got {:?}",
                r.statistic
            );
        }

        #[test]
        fn conditional_independent() {
            let data = ds(vec![
                ("x", vec![1., 1., 2., 2., 1., 1., 2., 2.]),
                ("y", vec![1., 2., 1., 2., 1., 2., 1., 2.]),
                ("z", vec![1., 1., 1., 1., 2., 2., 2., 2.]),
            ]);
            let r = ChiSquared::new().test(&data, 0, 1, &[2]).unwrap();
            assert!(r.statistic.unwrap().abs() < 1e-9);
            assert_eq!(r.dof, Some(2));
            assert!(r.p_value > 0.99);
        }

        #[test]
        fn wrong_column_kind_errors() {
            let data = Dataset::from_columns(vec![
                ("x".into(), ColumnKind::Continuous, vec![1., 2., 3.]),
                ("y".into(), ColumnKind::Discrete, vec![1., 2., 3.]),
            ])
            .unwrap();
            assert!(matches!(
                ChiSquared::new().test(&data, 0, 1, &[]),
                Err(CIError::WrongColumnKind(_))
            ));
        }
    }

    mod log_likelihood {
        use super::discrete_dataset as ds;
        use super::*;

        #[test]
        fn dependent_table_pins_lambda_and_effect_size() {
            // 2x3 dependent table (n=27, dof=2, Yates inert) pinning the log-likelihood
            // lambda wiring and Cramér's V effect size against scipy references.
            let x = vec![
                0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 1., 1., 1., 1., 1., 1., 1., 1., 1.,
                1., 1., 1., 1., 1., 1.,
            ];
            let y = vec![
                0., 0., 0., 0., 0., 0., 1., 1., 2., 2., 2., 2., 0., 0., 0., 1., 1., 1., 1., 1., 1.,
                1., 2., 2., 2., 2., 2.,
            ];
            let data = ds(vec![("x", x), ("y", y)]);
            let r = LogLikelihood::new().test(&data, 0, 1, &[]).unwrap();
            assert_eq!(r.dof, Some(2));
            assert!((r.statistic.unwrap() - 3.738_650_145_2).abs() < 1e-6);
            assert!((r.effect_size.unwrap() - 0.372_113_590_0).abs() < 1e-6);
        }
    }

    mod cressie_read {
        use super::discrete_dataset as ds;
        use super::*;

        #[test]
        fn balanced_independent_table_has_finite_effect_size() {
            // Cressie-Read on a balanced independent 2x2 ([[4,4],[4,4]]): O == E, so
            // the power-divergence statistic rounds to a tiny *negative* value. The
            // Cramér's V effect size must still be a finite 0.0, not NaN (regression
            // test for the cramers_v radicand clamp).
            let data = ds(vec![
                (
                    "x",
                    vec![
                        0., 0., 0., 0., 0., 0., 0., 0., 1., 1., 1., 1., 1., 1., 1., 1.,
                    ],
                ),
                (
                    "y",
                    vec![
                        0., 0., 0., 0., 1., 1., 1., 1., 0., 0., 0., 0., 1., 1., 1., 1.,
                    ],
                ),
            ]);
            let r = CressieRead::new().test(&data, 0, 1, &[]).unwrap();
            let effect = r.effect_size.expect("effect size should be present");
            assert!(
                effect.is_finite(),
                "effect size must be finite, got {effect}"
            );
            assert!(
                effect < 1e-9,
                "balanced independent table -> ~0 effect, got {effect}"
            );
        }

        #[test]
        fn dependent_table_pins_lambda_and_effect_size() {
            // 2x3 dependent table (n=27, dof=2, Yates inert) pinning the Cressie-Read
            // lambda wiring and Cramér's V effect size against scipy references.
            let x = vec![
                0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 1., 1., 1., 1., 1., 1., 1., 1., 1.,
                1., 1., 1., 1., 1., 1.,
            ];
            let y = vec![
                0., 0., 0., 0., 0., 0., 1., 1., 2., 2., 2., 2., 0., 0., 0., 1., 1., 1., 1., 1., 1.,
                1., 2., 2., 2., 2., 2.,
            ];
            let data = ds(vec![("x", x), ("y", y)]);
            let r = CressieRead::new().test(&data, 0, 1, &[]).unwrap();
            assert_eq!(r.dof, Some(2));
            assert!((r.statistic.unwrap() - 3.629_764_546_5).abs() < 1e-6);
            assert!((r.effect_size.unwrap() - 0.366_654_774_9).abs() < 1e-6);
        }
    }

    mod freeman_tukey {
        use super::discrete_dataset as ds;
        use super::*;

        #[test]
        fn dependent_table_pins_lambda_and_effect_size() {
            // 2x3 dependent table (n=27, dof=2, Yates inert) pinning the Freeman-Tukey
            // lambda wiring and Cramér's V effect size against scipy references.
            let x = vec![
                0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 1., 1., 1., 1., 1., 1., 1., 1., 1.,
                1., 1., 1., 1., 1., 1.,
            ];
            let y = vec![
                0., 0., 0., 0., 0., 0., 1., 1., 2., 2., 2., 2., 0., 0., 0., 1., 1., 1., 1., 1., 1.,
                1., 2., 2., 2., 2., 2.,
            ];
            let data = ds(vec![("x", x), ("y", y)]);
            let r = FreemanTukey::new().test(&data, 0, 1, &[]).unwrap();
            assert_eq!(r.dof, Some(2));
            assert!((r.statistic.unwrap() - 3.868_242_083_0).abs() < 1e-6);
            assert!((r.effect_size.unwrap() - 0.378_507_893_3).abs() < 1e-6);
        }
    }

    mod modified_likelihood {
        use super::discrete_dataset as ds;
        use super::*;

        #[test]
        fn structural_zero_gives_p_zero() {
            // A 3×3 table (dof != 1, so no Yates) with a structural zero in an
            // active row/column -> statistic +∞ -> p = 0.
            let data = ds(vec![
                ("x", vec![0., 0., 0., 0., 1., 1., 1., 1., 2., 2., 2., 2.]),
                ("y", vec![0., 0., 1., 1., 0., 0., 1., 1., 2., 2., 2., 2.]),
            ]);
            let r = ModifiedLikelihood::new().test(&data, 0, 1, &[]).unwrap();
            assert!(r.statistic.unwrap().is_infinite());
            // p is exactly 0 for an infinite statistic.
            assert!(r.p_value.total_cmp(&0.0).is_eq());
        }
    }
}
