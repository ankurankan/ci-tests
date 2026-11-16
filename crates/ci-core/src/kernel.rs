//! Kernel types and dense kernel-matrix helpers shared by HSIC and KCI.
//!
//! Points are row-major `faer::Mat<f64>` (n rows x d columns). All helpers
//! follow the pgmpy reference numerics (sklearn `RBF`, numpy median).

use std::collections::BTreeMap;

use faer::{Mat, MatRef};
use statrs::distribution::{ContinuousCDF, Gamma};

use crate::dataset::Dataset;
use crate::error::CiError;

/// A positive-definite kernel on standardized points.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Kernel {
    /// Gaussian kernel `exp(-||a - b||^2 / (2 l^2))`.
    Rbf {
        /// Length scale `l`; must be finite and positive.
        length_scale: f64,
    },
    /// Linear kernel `a . b`.
    Linear,
}

/// How a default RBF length scale is chosen.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum Bandwidth {
    /// Fixed sample-size heuristic.
    #[default]
    Heuristic,
    /// Median pairwise distance rule.
    Median,
}

/// Which kernel(s) to use for the columns of a query.
#[derive(Debug, Clone, PartialEq, Default)]
pub enum KernelChoice {
    /// Test-specific default kernel.
    #[default]
    Auto,
    /// One kernel for every column.
    All(Kernel),
    /// A kernel per named column.
    PerColumn(BTreeMap<String, Kernel>),
}

impl Kernel {
    /// Check the kernel parameters.
    ///
    /// # Errors
    /// [`CiError::InvalidConfig`] if an RBF length scale is not finite and > 0.
    pub fn validate(&self) -> Result<(), CiError> {
        if let Kernel::Rbf { length_scale } = *self {
            if !(length_scale.is_finite() && length_scale > 0.0) {
                return Err(CiError::InvalidConfig(format!(
                    "RBF length_scale must be finite and > 0, got {length_scale}"
                )));
            }
        }
        Ok(())
    }
}

impl KernelChoice {
    /// Validate every kernel and that every `PerColumn` key names a column.
    ///
    /// # Errors
    /// [`CiError::InvalidConfig`] for a bad kernel, [`CiError::UnknownColumn`]
    /// for an unknown column name.
    pub fn validate(&self, data: &Dataset) -> Result<(), CiError> {
        match self {
            KernelChoice::Auto => Ok(()),
            KernelChoice::All(k) => k.validate(),
            KernelChoice::PerColumn(map) => {
                for (name, k) in map {
                    if data.index_of(name).is_none() {
                        return Err(CiError::UnknownColumn(name.clone()));
                    }
                    k.validate()?;
                }
                Ok(())
            }
        }
    }
}

/// Reject sample sizes whose dense `n x n` matrix would overflow `isize`.
pub(crate) fn dense_len_guard(n: usize) -> Result<(), CiError> {
    let ok = n
        .checked_mul(n)
        .and_then(|v| v.checked_mul(8))
        .is_some_and(|b| isize::try_from(b).is_ok());
    if ok {
        Ok(())
    } else {
        Err(CiError::DegenerateData(format!(
            "too many rows ({n}) for a dense kernel matrix"
        )))
    }
}

/// Stack `cols`, each standardized (ddof = 1) and multiplied by `scale`.
pub(crate) fn standardized(
    data: &Dataset,
    cols: &[usize],
    scale: f64,
) -> Result<Mat<f64>, CiError> {
    let n = data.n_rows();
    if n < 2 {
        return Err(CiError::DegenerateData(
            "at least 2 rows are required".into(),
        ));
    }
    let mut out = Mat::<f64>::zeros(n, cols.len());
    #[allow(clippy::cast_precision_loss)]
    let nf = n as f64;
    for (j, &c) in cols.iter().enumerate() {
        let v = data.continuous(c)?;
        let mean = v.iter().sum::<f64>() / nf;
        let var = v.iter().map(|x| (x - mean) * (x - mean)).sum::<f64>() / (nf - 1.0);
        let sd = var.sqrt();
        if !(sd.is_finite() && sd > 0.0) {
            return Err(CiError::DegenerateData(format!(
                "column {} has zero or non-finite variance",
                data.name_of(c).unwrap_or("?")
            )));
        }
        for (i, x) in v.iter().enumerate() {
            out[(i, j)] = (x - mean) / sd * scale;
        }
    }
    Ok(out)
}

/// Dense kernel matrix over the rows of `points`.
#[must_use]
#[allow(clippy::many_single_char_names)]
pub(crate) fn kernel_matrix(kernel: Kernel, points: MatRef<'_, f64>) -> Mat<f64> {
    let n = points.nrows();
    let d = points.ncols();
    let mut k = Mat::<f64>::zeros(n, n);
    match kernel {
        Kernel::Rbf { length_scale } => {
            for i in 0..n {
                for j in i..n {
                    let mut s = 0.0;
                    for c in 0..d {
                        let diff = points[(i, c)] / length_scale - points[(j, c)] / length_scale;
                        s += diff * diff;
                    }
                    let v = (-0.5 * s).exp();
                    k[(i, j)] = v;
                    k[(j, i)] = v;
                }
            }
        }
        Kernel::Linear => {
            for i in 0..n {
                for j in i..n {
                    let mut s = 0.0;
                    for c in 0..d {
                        s += points[(i, c)] * points[(j, c)];
                    }
                    k[(i, j)] = s;
                    k[(j, i)] = s;
                }
            }
        }
    }
    k
}

/// In-place centering: `K - colmean - colmean[:, None] + mean(colmean)`.
pub(crate) fn center(k: &mut Mat<f64>) {
    let n = k.nrows();
    if n == 0 {
        return;
    }
    #[allow(clippy::cast_precision_loss)]
    let nf = n as f64;
    let colmean: Vec<f64> = (0..k.ncols())
        .map(|j| (0..n).map(|i| k[(i, j)]).sum::<f64>() / nf)
        .collect();
    let total = colmean.iter().sum::<f64>() / nf;
    for j in 0..k.ncols() {
        for i in 0..n {
            k[(i, j)] = k[(i, j)] - colmean[j] - colmean[i] + total;
        }
    }
}

/// Median pairwise Euclidean distance (zeros dropped) divided by sqrt(2);
/// `1.0` if there is no non-zero distance.
#[must_use]
pub(crate) fn median_length_scale(points: MatRef<'_, f64>) -> f64 {
    let n = points.nrows();
    let d = points.ncols();
    let mut dist = Vec::with_capacity(n * n.saturating_sub(1) / 2);
    for i in 0..n {
        for j in (i + 1)..n {
            let mut s = 0.0;
            for c in 0..d {
                let diff = points[(i, c)] - points[(j, c)];
                s += diff * diff;
            }
            let r = s.sqrt();
            if r > 0.0 {
                dist.push(r);
            }
        }
    }
    let m = dist.len();
    if m == 0 {
        return 1.0;
    }
    let cmp = |a: &f64, b: &f64| a.total_cmp(b);
    let hi_idx = m / 2;
    let (lower, hi, _) = dist.select_nth_unstable_by(hi_idx, cmp);
    let hi = *hi;
    let median = if m % 2 == 1 {
        hi
    } else {
        let lo = lower.iter().copied().max_by(cmp).unwrap_or(hi);
        0.5 * (lo + hi)
    };
    median / std::f64::consts::SQRT_2
}

/// Gamma-approximation p-value from the null mean and variance.
pub(crate) fn gamma_pvalue(stat: f64, mean: f64, var: f64) -> Result<f64, CiError> {
    if var <= 0.0 || mean <= 0.0 {
        return Ok(1.0);
    }
    let shape = mean * mean / var;
    let scale = var / mean;
    let g = Gamma::new(shape, 1.0 / scale)
        .map_err(|e| CiError::Numeric(format!("gamma construction failed: {e}")))?;
    Ok(g.sf(stat))
}

#[cfg(test)]
#[allow(clippy::float_cmp)]
mod tests {
    use super::*;
    use crate::dataset::ColumnKind;

    fn col(v: &[f64]) -> Mat<f64> {
        Mat::from_fn(v.len(), 1, |i, _| v[i])
    }

    #[test]
    fn rbf_and_linear_entries() {
        let p = col(&[0.0, 1.0, 3.0]);
        let k = kernel_matrix(Kernel::Rbf { length_scale: 2.0 }, p.as_ref());
        assert!((k[(0, 1)] - (-0.125f64).exp()).abs() < 1e-15);
        assert!((k[(0, 2)] - (-1.125f64).exp()).abs() < 1e-15);
        for i in 0..3 {
            assert_eq!(k[(i, i)], 1.0);
        }
        let l = kernel_matrix(Kernel::Linear, p.as_ref());
        assert_eq!(l[(1, 2)], 3.0);
    }

    #[test]
    fn centering_zeroes_row_and_column_sums() {
        let p = col(&[0.3, -1.0, 2.0, 0.7]);
        let mut k = kernel_matrix(Kernel::Rbf { length_scale: 1.0 }, p.as_ref());
        center(&mut k);
        for i in 0..4 {
            let r: f64 = (0..4).map(|j| k[(i, j)]).sum();
            let c: f64 = (0..4).map(|j| k[(j, i)]).sum();
            assert!(r.abs() < 1e-12 && c.abs() < 1e-12);
        }
    }

    #[test]
    fn median_length_scale_drops_zero_distances() {
        let s2 = std::f64::consts::SQRT_2;
        assert!((median_length_scale(col(&[0.0, 1.0, 3.0]).as_ref()) - 2.0 / s2).abs() < 1e-15);
        assert!((median_length_scale(col(&[0.0, 0.0, 1.0]).as_ref()) - 1.0 / s2).abs() < 1e-15);
        assert_eq!(median_length_scale(col(&[5.0, 5.0]).as_ref()), 1.0);
        // even count: distances {1,2,3,4,...}
        let m = median_length_scale(col(&[0.0, 1.0, 2.0]).as_ref());
        assert!((m - 1.0 / s2).abs() < 1e-15); // {1,1,2} -> 1
    }

    #[test]
    fn gamma_pvalue_closed_form_and_degenerate_moments() {
        let p = gamma_pvalue(3.0, 2.0, 2.0).unwrap();
        assert!((p - 0.199_148_273_471_455_78).abs() < 1e-14);
        assert_eq!(gamma_pvalue(3.0, 0.0, 2.0).unwrap(), 1.0);
        assert_eq!(gamma_pvalue(3.0, -1.0, 2.0).unwrap(), 1.0);
        assert_eq!(gamma_pvalue(3.0, 2.0, 0.0).unwrap(), 1.0);
    }

    #[test]
    fn standardized_rejects_constant_and_discrete_columns() {
        let d = Dataset::from_columns(vec![
            ("a".into(), ColumnKind::Continuous, vec![1.0, 2.0, 4.0]),
            ("c".into(), ColumnKind::Continuous, vec![1.0, 1.0, 1.0]),
            ("d".into(), ColumnKind::Discrete, vec![0.0, 1.0, 0.0]),
        ])
        .unwrap();
        let m = standardized(&d, &[0], 2.0).unwrap();
        let sum: f64 = (0..3).map(|i| m[(i, 0)]).sum();
        assert!(sum.abs() < 1e-12);
        let ss: f64 = (0..3).map(|i| m[(i, 0)] * m[(i, 0)]).sum();
        assert!((ss - 4.0 * 2.0).abs() < 1e-12);
        assert!(matches!(
            standardized(&d, &[1], 1.0),
            Err(CiError::DegenerateData(_))
        ));
        assert!(matches!(
            standardized(&d, &[2], 1.0),
            Err(CiError::WrongColumnKind(_))
        ));
    }

    #[test]
    fn kernel_validation_rejects_bad_length_scales() {
        for l in [0.0, -1.0, f64::NAN, f64::INFINITY] {
            assert!(matches!(
                Kernel::Rbf { length_scale: l }.validate(),
                Err(CiError::InvalidConfig(_))
            ));
        }
        assert!(Kernel::Rbf { length_scale: 0.5 }.validate().is_ok());
        assert!(Kernel::Linear.validate().is_ok());
    }

    #[test]
    fn per_column_choice_rejects_unknown_columns() {
        let d = Dataset::from_columns(vec![("a".into(), ColumnKind::Continuous, vec![1.0, 2.0])])
            .unwrap();
        let mut m = BTreeMap::new();
        m.insert("a".to_string(), Kernel::Linear);
        assert!(KernelChoice::PerColumn(m.clone()).validate(&d).is_ok());
        m.insert("zz".to_string(), Kernel::Linear);
        assert!(matches!(
            KernelChoice::PerColumn(m).validate(&d),
            Err(CiError::UnknownColumn(_))
        ));
    }

    #[test]
    fn dense_len_guard_rejects_overflow() {
        assert!(matches!(
            dense_len_guard(usize::MAX / 2),
            Err(CiError::DegenerateData(_))
        ));
        assert!(dense_len_guard(1000).is_ok());
    }
}
