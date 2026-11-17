//! Linear residualization shared by the GCM and Pillai tests.
//!
//! Builds the `[1, Z]` design matrix (discrete columns one-hot encoded with
//! level 0 dropped), the target block of a variable (continuous values, or
//! indicators of all but the last level for a discrete column — a linear
//! probability model), and computes OLS residuals of many targets at once via
//! Householder QR.

use faer::{Mat, MatRef};

use crate::dataset::Dataset;
use crate::error::CIError;

/// Relative pivot tolerance (against the column's own norm) for declaring the
/// design rank-deficient.
const RANK_TOL: f64 = 1e-10;

/// Design matrix `[1, Z]` (n × d). A continuous `z` entry contributes its
/// values; a discrete entry with K levels contributes indicators of levels
/// `1..K` (level code 0 is dropped).
///
/// # Errors
///
/// Returns [`CIError::UnknownColumn`] for an out-of-range index.
pub(crate) fn design_matrix(data: &Dataset, z: &[usize]) -> Result<Mat<f64>, CIError> {
    let n = data.n_rows();
    let mut cols: Vec<Vec<f64>> = vec![vec![1.0; n]];
    for &idx in z {
        if let Ok(values) = data.continuous(idx) {
            cols.push(values.to_vec());
        } else {
            let (codes, card) = data.discrete(idx)?;
            for level in 1..card {
                cols.push(
                    codes
                        .iter()
                        .map(|&c| f64::from(u8::from(c == level)))
                        .collect(),
                );
            }
        }
    }
    Ok(Mat::from_fn(n, cols.len(), |i, j| cols[j][i]))
}

/// Target block of column `col`: n × 1 values if continuous; for a discrete
/// column with K levels, indicators of codes `0..K-1` (n × (K−1)).
///
/// # Errors
///
/// Returns [`CIError::DegenerateData`] if a discrete column has one level, or
/// [`CIError::UnknownColumn`] for an out-of-range index.
pub(crate) fn target_block(data: &Dataset, col: usize) -> Result<Mat<f64>, CIError> {
    let n = data.n_rows();
    if let Ok(values) = data.continuous(col) {
        return Ok(Mat::from_fn(n, 1, |i, _| values[i]));
    }
    let (codes, card) = data.discrete(col)?;
    if card < 2 {
        return Err(CIError::DegenerateData(format!(
            "column {col} has a single observed level"
        )));
    }
    Ok(Mat::from_fn(n, card - 1, |i, j| {
        f64::from(u8::from(codes[i] == j))
    }))
}

/// Applies the Householder reflector `I - 2 v vᵀ` (unit `v`, acting on rows
/// `j..`) to `col`.
fn reflect(v: &[f64], j: usize, col: &mut [f64]) {
    let dot: f64 = v.iter().zip(&col[j..]).map(|(a, b)| a * b).sum();
    for (c, a) in col[j..].iter_mut().zip(v) {
        *c -= 2.0 * dot * a;
    }
}

/// OLS residuals of every column of `targets` on `design`, by Householder QR.
///
/// # Errors
///
/// Returns [`CIError::DegenerateData`] if `design` is rank-deficient (a pivot
/// below `1e-10` of its own column's norm) or has no more rows than columns, or if the
/// row counts differ.
pub(crate) fn ols_residuals_multi(
    design: MatRef<'_, f64>,
    targets: MatRef<'_, f64>,
) -> Result<Mat<f64>, CIError> {
    let (n, d) = (design.nrows(), design.ncols());
    if targets.nrows() != n {
        return Err(CIError::DimensionMismatch(format!(
            "design has {n} rows but targets have {}",
            targets.nrows()
        )));
    }
    if n <= d {
        return Err(CIError::DegenerateData(format!(
            "design matrix [1, Z] is rank-deficient: {n} rows for {d} columns"
        )));
    }
    let mut a: Vec<Vec<f64>> = (0..d)
        .map(|j| (0..n).map(|i| design[(i, j)]).collect())
        .collect();
    let mut reflectors: Vec<Vec<f64>> = Vec::with_capacity(d);
    let mut pivots = Vec::with_capacity(d);
    // Each pivot is judged against its own column's norm, so rescaling a
    // conditioning column does not change the rank decision.
    let col_norms: Vec<f64> = a
        .iter()
        .map(|c| c.iter().map(|x| x * x).sum::<f64>().sqrt())
        .collect();
    for j in 0..d {
        let norm = a[j][j..].iter().map(|x| x * x).sum::<f64>().sqrt();
        pivots.push(norm);
        let mut v = a[j][j..].to_vec();
        let sign = if v[0] < 0.0 { -1.0 } else { 1.0 };
        v[0] += sign * norm;
        let vnorm = v.iter().map(|x| x * x).sum::<f64>().sqrt();
        if vnorm > 0.0 {
            for x in &mut v {
                *x /= vnorm;
            }
            for col in &mut a[j..] {
                reflect(&v, j, col);
            }
        }
        reflectors.push(v);
    }
    if pivots
        .iter()
        .zip(&col_norms)
        .any(|(&p, &c)| !p.is_finite() || !c.is_finite() || p <= RANK_TOL * c)
    {
        return Err(CIError::DegenerateData(
            "design matrix [1, Z] is rank-deficient (collinear or constant conditioning columns)"
                .to_string(),
        ));
    }
    let mut out = Mat::zeros(n, targets.ncols());
    for c in 0..targets.ncols() {
        let mut t: Vec<f64> = (0..n).map(|i| targets[(i, c)]).collect();
        for (j, v) in reflectors.iter().enumerate() {
            reflect(v, j, &mut t);
        }
        for x in &mut t[..d] {
            *x = 0.0;
        }
        for (j, v) in reflectors.iter().enumerate().rev() {
            reflect(v, j, &mut t);
        }
        for (i, x) in t.into_iter().enumerate() {
            out[(i, c)] = x;
        }
    }
    Ok(out)
}

#[cfg(test)]
#[allow(
    clippy::cast_precision_loss,
    clippy::cast_possible_truncation,
    clippy::cast_sign_loss,
    clippy::float_cmp,
    clippy::many_single_char_names
)]
mod tests {
    use super::*;
    use crate::dataset::ColumnKind;
    use crate::rng::SplitMix64;

    fn uniform(rng: &mut SplitMix64) -> f64 {
        #[allow(clippy::cast_precision_loss)]
        let u = (rng.next_u64() >> 11) as f64 / (1u64 << 53) as f64;
        u
    }

    fn ds(cols: Vec<(&str, ColumnKind, Vec<f64>)>) -> Dataset {
        Dataset::from_columns(
            cols.into_iter()
                .map(|(n, k, v)| (n.to_string(), k, v))
                .collect(),
        )
        .unwrap()
    }

    fn max_abs_diff(a: &Mat<f64>, b: &Mat<f64>) -> f64 {
        assert_eq!((a.nrows(), a.ncols()), (b.nrows(), b.ncols()));
        let mut m = 0.0_f64;
        for i in 0..a.nrows() {
            for j in 0..a.ncols() {
                m = m.max((a[(i, j)] - b[(i, j)]).abs());
            }
        }
        m
    }

    #[test]
    fn empty_z_residuals_are_centered_targets() {
        let data = ds(vec![("t", ColumnKind::Continuous, vec![1., 2., 3., 6.])]);
        let d = design_matrix(&data, &[]).unwrap();
        let t = target_block(&data, 0).unwrap();
        let r = ols_residuals_multi(d.as_ref(), t.as_ref()).unwrap();
        for (i, e) in [-2., -1., 0., 3.].iter().enumerate() {
            assert!((r[(i, 0)] - e).abs() < 1e-12);
        }
    }

    #[test]
    fn residuals_are_orthogonal_to_design() {
        let n = 60;
        let mut rng = SplitMix64::new(7);
        let c1: Vec<f64> = (0..n).map(|_| uniform(&mut rng)).collect();
        let c2: Vec<f64> = (0..n).map(|_| uniform(&mut rng) * 100.0).collect();
        let g: Vec<f64> = (0..n).map(|_| (rng.next_u64() % 3) as f64).collect();
        let t1: Vec<f64> = (0..n).map(|_| uniform(&mut rng)).collect();
        let t2: Vec<f64> = (0..n).map(|_| (rng.next_u64() % 4) as f64).collect();
        let data = ds(vec![
            ("c1", ColumnKind::Continuous, c1),
            ("c2", ColumnKind::Continuous, c2),
            ("g", ColumnKind::Discrete, g),
            ("t1", ColumnKind::Continuous, t1),
            ("t2", ColumnKind::Discrete, t2),
        ]);
        let d = design_matrix(&data, &[0, 1, 2]).unwrap();
        let b1 = target_block(&data, 3).unwrap();
        let b2 = target_block(&data, 4).unwrap();
        let t = Mat::from_fn(n, b1.ncols() + b2.ncols(), |i, j| {
            if j < b1.ncols() {
                b1[(i, j)]
            } else {
                b2[(i, j - b1.ncols())]
            }
        });
        let r = ols_residuals_multi(d.as_ref(), t.as_ref()).unwrap();
        let rnorm: f64 = (0..n)
            .flat_map(|i| (0..r.ncols()).map(move |j| (i, j)))
            .map(|(i, j)| r[(i, j)].powi(2))
            .sum::<f64>()
            .sqrt();
        for a in 0..d.ncols() {
            let dn: f64 = (0..n).map(|i| d[(i, a)].powi(2)).sum::<f64>().sqrt();
            for b in 0..r.ncols() {
                let dot: f64 = (0..n).map(|i| d[(i, a)] * r[(i, b)]).sum();
                assert!(dot.abs() <= 1e-9 * dn * rnorm.max(1.0), "dot {dot}");
            }
        }
    }

    #[test]
    fn discrete_z_one_hot_matches_full_dummies_fit() {
        let z = vec![0., 1., 2., 1., 0., 2., 2., 1., 0., 0.];
        let t = vec![0.3, 1.2, -0.7, 2.2, 0.9, 1.1, -0.2, 0.4, 3.0, 1.7];
        let data = ds(vec![
            ("z", ColumnKind::Discrete, z.clone()),
            ("t", ColumnKind::Continuous, t),
        ]);
        let tb = target_block(&data, 1).unwrap();
        let r1 =
            ols_residuals_multi(design_matrix(&data, &[0]).unwrap().as_ref(), tb.as_ref()).unwrap();
        let full = Mat::from_fn(z.len(), 3, |i, j| f64::from(u8::from(z[i] as usize == j)));
        let r2 = ols_residuals_multi(full.as_ref(), tb.as_ref()).unwrap();
        assert!(max_abs_diff(&r1, &r2) < 1e-12);
    }

    #[test]
    fn discrete_target_block_drops_last_level() {
        let data = ds(vec![("d", ColumnKind::Discrete, vec![0., 1., 2., 0., 2.])]);
        let b = target_block(&data, 0).unwrap();
        assert_eq!((b.nrows(), b.ncols()), (5, 2));
        let c0 = [1., 0., 0., 1., 0.];
        let c1 = [0., 1., 0., 0., 0.];
        for i in 0..5 {
            assert_eq!(b[(i, 0)], c0[i]);
            assert_eq!(b[(i, 1)], c1[i]);
        }
    }

    #[test]
    fn single_level_target_is_degenerate() {
        let data = ds(vec![("d", ColumnKind::Discrete, vec![4., 4., 4.])]);
        assert!(matches!(
            target_block(&data, 0),
            Err(CIError::DegenerateData(_))
        ));
    }

    #[test]
    fn rank_deficient_design_is_degenerate() {
        let a = vec![1., 2., 3., 5., 4., 7.];
        let data = ds(vec![
            ("a", ColumnKind::Continuous, a.clone()),
            ("b", ColumnKind::Continuous, a),
            ("t", ColumnKind::Continuous, vec![1., 0., 2., 1., 5., 3.]),
        ]);
        let t = target_block(&data, 2).unwrap();
        let d = design_matrix(&data, &[0, 1]).unwrap();
        assert!(matches!(
            ols_residuals_multi(d.as_ref(), t.as_ref()),
            Err(CIError::DegenerateData(_))
        ));
        let data = ds(vec![
            ("a", ColumnKind::Continuous, vec![1., 2., 4.]),
            ("b", ColumnKind::Continuous, vec![3., 1., 9.]),
            ("c", ColumnKind::Continuous, vec![0., 5., 1.]),
            ("t", ColumnKind::Continuous, vec![1., 0., 2.]),
        ]);
        let t = target_block(&data, 3).unwrap();
        let d = design_matrix(&data, &[0, 1, 2]).unwrap();
        assert!(matches!(
            ols_residuals_multi(d.as_ref(), t.as_ref()),
            Err(CIError::DegenerateData(_))
        ));
    }

    #[test]
    fn multi_target_matches_single_target_fits() {
        let mut rng = SplitMix64::new(11);
        let n = 30;
        let cols: Vec<Vec<f64>> = (0..3)
            .map(|_| (0..n).map(|_| uniform(&mut rng)).collect())
            .collect();
        let data = ds(vec![
            ("z", ColumnKind::Continuous, cols[0].clone()),
            ("t1", ColumnKind::Continuous, cols[1].clone()),
            ("t2", ColumnKind::Continuous, cols[2].clone()),
        ]);
        let d = design_matrix(&data, &[0]).unwrap();
        let both = Mat::from_fn(n, 2, |i, j| cols[j + 1][i]);
        let r = ols_residuals_multi(d.as_ref(), both.as_ref()).unwrap();
        for j in 0..2 {
            let one = Mat::from_fn(n, 1, |i, _| cols[j + 1][i]);
            let rj = ols_residuals_multi(d.as_ref(), one.as_ref()).unwrap();
            for i in 0..n {
                assert!((r[(i, j)] - rj[(i, 0)]).abs() < 1e-12);
            }
        }
    }
}
