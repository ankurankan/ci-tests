//! Pearson / partial-correlation conditional-independence test (continuous).

use statrs::distribution::{ContinuousCDF, StudentsT};

use crate::correlation::partial_correlation;
use crate::dataset::Dataset;
use crate::error::CiError;
use crate::strategy::{CITest, CiResult, DataType, IndependenceRule, TestMeta};

/// Pearson correlation test. With a non-empty conditioning set it computes the
/// partial correlation by regressing X and Y on `[1, Z]` (intercept included)
/// and correlating the residuals.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct PearsonCorrelation;

impl PearsonCorrelation {
    /// Construct the test (no configuration in this slice).
    #[must_use]
    pub fn new() -> Self {
        Self
    }
}

/// Two-tailed p-value for H₀: ρ = 0 from `r` and `dof` via the t-distribution.
///
/// # Errors
///
/// Returns [`CiError::DegenerateData`] if `|r| == 1` (t undefined) and
/// [`CiError::Numeric`] if the t-distribution construction fails.
fn correlation_p_value(r: f64, dof: usize) -> Result<f64, CiError> {
    if (1.0 - r * r) <= 0.0 {
        return Err(CiError::DegenerateData(
            "correlation is ±1; t-statistic is undefined".to_string(),
        ));
    }
    #[allow(clippy::cast_precision_loss)]
    let dof_f = dof as f64;
    let t = r * (dof_f / (1.0 - r * r)).sqrt();
    let dist = StudentsT::new(0.0, 1.0, dof_f)
        .map_err(|e| CiError::Numeric(format!("Student's t distribution: {e}")))?;
    Ok(2.0 * dist.sf(t.abs()))
}

impl CITest for PearsonCorrelation {
    fn test_impl(
        &self,
        data: &Dataset,
        x: usize,
        y: usize,
        z: &[usize],
    ) -> Result<CiResult, CiError> {
        let (r, dof) = partial_correlation(data, x, y, z)?;
        let p_value = correlation_p_value(r, dof)?;
        Ok(CiResult {
            statistic: Some(r),
            p_value,
            dof: Some(dof),
            effect_size: Some(r.abs()),
        })
    }

    fn meta(&self) -> TestMeta {
        TestMeta {
            name: "pearson_correlation",
            data_types: &[DataType::Continuous],
            symmetric: true,
            rule: IndependenceRule::PValueGe,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::dataset::ColumnKind;

    fn ds(cols: Vec<(&str, Vec<f64>)>) -> Dataset {
        Dataset::from_columns(
            cols.into_iter()
                .map(|(n, v)| (n.to_string(), ColumnKind::Continuous, v))
                .collect(),
        )
        .unwrap()
    }

    #[test]
    fn unconditional_strong_correlation() {
        // Strongly (but not perfectly) correlated, so 1 - r^2 > 0.
        let data = ds(vec![
            ("x", vec![1., 2., 3., 4., 5.]),
            ("y", vec![2., 4.1, 5.9, 8.2, 9.8]),
        ]);
        let r = PearsonCorrelation::new().test(&data, 0, 1, &[]).unwrap();
        assert!(r.statistic.unwrap() > 0.9);
        assert_eq!(r.dof, Some(3));
        assert!(r.p_value < 0.05);
        assert!((r.effect_size.unwrap() - r.statistic.unwrap().abs()).abs() < 1e-12);
    }

    #[test]
    fn perfect_correlation_is_degenerate() {
        // r == 1 exactly -> t-statistic undefined; report a clear error.
        let data = ds(vec![
            ("x", vec![1., 2., 3., 4., 5.]),
            ("y", vec![2., 4., 6., 8., 10.]),
        ]);
        assert!(matches!(
            PearsonCorrelation::new().test(&data, 0, 1, &[]),
            Err(CiError::DegenerateData(_))
        ));
    }

    #[test]
    fn constant_input_is_degenerate_not_panic() {
        let data = ds(vec![
            ("x", vec![1., 1., 1., 1., 1.]),
            ("y", vec![2., 4., 6., 8., 10.]),
        ]);
        assert!(matches!(
            PearsonCorrelation::new().test(&data, 0, 1, &[]),
            Err(CiError::DegenerateData(_))
        ));
    }

    #[test]
    fn conditional_uses_intercept() {
        // y = 2*z + 5, x = 3*z + 1: after regressing out [1, z] residuals are ~0.
        let z = vec![1., 2., 3., 4., 5., 6., 7., 8.];
        let x: Vec<f64> = z.iter().map(|v| 3.0 * v + 1.0).collect();
        let y: Vec<f64> = z.iter().map(|v| 2.0 * v + 5.0).collect();
        let data = ds(vec![("x", x), ("y", y), ("z", z)]);
        // residuals are ~0 -> constant -> degenerate (exact collinear case).
        let res = PearsonCorrelation::new().test(&data, 0, 1, &[2]);
        assert!(matches!(res, Err(CiError::DegenerateData(_))));
    }

    #[test]
    fn dof_accounts_for_conditioning_set() {
        let z1 = vec![0.1, 0.9, 0.2, 0.8, 0.3, 0.7, 0.4, 0.6, 0.5, 1.1];
        let z2 = vec![1.1, 0.2, 0.7, 0.3, 0.9, 0.4, 0.8, 0.1, 0.6, 0.5];
        let x = vec![0.5, 0.4, 0.6, 0.2, 0.9, 0.1, 0.7, 0.3, 0.8, 0.2];
        let y = vec![0.2, 0.7, 0.1, 0.8, 0.3, 0.9, 0.4, 0.6, 0.5, 0.7];
        let data = ds(vec![("x", x), ("y", y), ("z1", z1), ("z2", z2)]);
        let r = PearsonCorrelation::new()
            .test(&data, 0, 1, &[2, 3])
            .unwrap();
        // n - |Z| - 2 = 10 - 2 - 2 = 6.
        assert_eq!(r.dof, Some(6));
    }

    #[test]
    fn wrong_kind_errors() {
        let data = Dataset::from_columns(vec![
            ("x".into(), ColumnKind::Discrete, vec![1., 2., 3.]),
            ("y".into(), ColumnKind::Continuous, vec![1., 2., 3.]),
        ])
        .unwrap();
        assert!(matches!(
            PearsonCorrelation::new().test(&data, 0, 1, &[]),
            Err(CiError::WrongColumnKind(_))
        ));
    }
}
