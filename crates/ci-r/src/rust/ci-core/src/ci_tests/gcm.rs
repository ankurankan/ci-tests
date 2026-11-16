//! Generalized covariance measure (GCM) conditional-independence test
//! (continuous data), after Shah & Peters (2020).
//!
//! X and Y are linearly regressed on `[1, Z]`; with residuals `r_x`, `r_y` and
//! `u = r_x ∘ r_y`, the statistic is `T = Σu / (√n · std(u))` (population
//! standard deviation), asymptotically N(0, 1) under H₀. The p-value is
//! `2 · P(N > |T|)` and the effect size is `|cor(r_x, r_y)|`.

use faer::Mat;
use statrs::distribution::{ContinuousCDF, Normal};

use crate::dataset::Dataset;
use crate::error::CiError;
use crate::residual::{design_matrix, ols_residuals_multi};
use crate::strategy::{CITest, CiResult, DataType, IndependenceRule, TestMeta};

/// Relative threshold below which a residual is treated as exactly zero.
const RESIDUAL_TOL: f64 = 1e-10;

/// Generalized covariance measure test (linear residualization).
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct Gcm;

impl Gcm {
    /// Construct the test (no configuration).
    #[must_use]
    pub fn new() -> Self {
        Self
    }
}

/// Residuals of continuous column `col` on `design`, as a plain vector.
fn residual_of(
    data: &Dataset,
    design: &Mat<f64>,
    col: usize,
    name: &str,
) -> Result<Vec<f64>, CiError> {
    let values = data.continuous(col)?;
    let n = values.len();
    let target = Mat::from_fn(n, 1, |i, _| values[i]);
    let res = ols_residuals_multi(design.as_ref(), target.as_ref())?;
    let r: Vec<f64> = (0..n).map(|i| res[(i, 0)]).collect();
    let max_abs = values.iter().fold(0.0_f64, |m, v| m.max(v.abs()));
    let (lo, hi) = values
        .iter()
        .fold((f64::INFINITY, f64::NEG_INFINITY), |(l, h), &v| {
            (l.min(v), h.max(v))
        });
    if lo >= hi {
        return Err(CiError::DegenerateData(format!("{name} is constant")));
    }
    #[allow(clippy::cast_precision_loss)]
    let nf = n as f64;
    #[allow(clippy::cast_precision_loss)]
    let mean = values.iter().sum::<f64>() / nf;
    let scale: f64 = values.iter().map(|v| (v - mean).powi(2)).sum();
    let res_ss: f64 = r.iter().map(|v| v * v).sum();
    let noise = nf * f64::EPSILON * f64::EPSILON * max_abs * max_abs;
    if !res_ss.is_finite() || res_ss <= RESIDUAL_TOL * RESIDUAL_TOL * scale + noise {
        return Err(CiError::DegenerateData(format!(
            "residual of {name} given Z has no variance"
        )));
    }
    Ok(r)
}

#[allow(clippy::many_single_char_names, clippy::similar_names)] // x, y, z, t, n are the standard names
impl CITest for Gcm {
    fn test_impl(
        &self,
        data: &Dataset,
        x: usize,
        y: usize,
        z: &[usize],
    ) -> Result<CiResult, CiError> {
        data.continuous(x)?;
        data.continuous(y)?;
        for &c in z {
            data.continuous(c)?;
        }
        let design = design_matrix(data, z)?;
        let rx = residual_of(data, &design, x, "X")?;
        let ry = residual_of(data, &design, y, "Y")?;

        #[allow(clippy::cast_precision_loss)]
        let n = rx.len() as f64;
        let u: Vec<f64> = rx.iter().zip(&ry).map(|(a, b)| a * b).collect();
        let sum_u: f64 = u.iter().sum();
        let mean_u = sum_u / n;
        let std_u = (u.iter().map(|v| (v - mean_u).powi(2)).sum::<f64>() / n).sqrt();
        if !(std_u.is_finite() && std_u > 0.0) {
            return Err(CiError::DegenerateData(
                "residual products have zero variance".to_string(),
            ));
        }
        let t = sum_u / (n.sqrt() * std_u);

        let normal = Normal::new(0.0, 1.0)
            .map_err(|e| CiError::Numeric(format!("normal distribution: {e}")))?;
        let p_value = 2.0 * normal.sf(t.abs());

        let mx = rx.iter().sum::<f64>() / n;
        let my = ry.iter().sum::<f64>() / n;
        let (mut cov_xy, mut var_x, mut var_y) = (0.0, 0.0, 0.0);
        for (a, b) in rx.iter().zip(&ry) {
            cov_xy += (a - mx) * (b - my);
            var_x += (a - mx).powi(2);
            var_y += (b - my).powi(2);
        }
        let effect = (cov_xy / (var_x.sqrt() * var_y.sqrt())).abs();
        if !effect.is_finite() {
            return Err(CiError::DegenerateData(
                "residual correlation is undefined".to_string(),
            ));
        }
        Ok(CiResult {
            statistic: Some(t),
            p_value,
            dof: None,
            effect_size: Some(effect),
        })
    }

    fn meta(&self) -> TestMeta {
        TestMeta {
            name: "gcm",
            data_types: &[DataType::Continuous],
            symmetric: true,
            rule: IndependenceRule::PValueGe,
        }
    }
}

#[cfg(test)]
#[allow(
    clippy::cast_precision_loss,
    clippy::many_single_char_names,
    clippy::needless_range_loop,
    clippy::unreadable_literal
)] // test helpers: small n, explicit math
mod tests {
    use super::*;
    use crate::dataset::ColumnKind;

    fn lcg(n: usize, seed: u64) -> Vec<f64> {
        let mut s = seed;
        (0..n)
            .map(|_| {
                s = s
                    .wrapping_mul(6364136223846793005)
                    .wrapping_add(1442695040888963407);
                #[allow(clippy::cast_precision_loss)]
                let v = (s >> 11) as f64 / (1u64 << 53) as f64;
                v - 0.5
            })
            .collect()
    }

    fn cols(n: usize) -> (Vec<f64>, Vec<f64>, Vec<f64>, Vec<f64>) {
        let z1 = lcg(n, 1);
        let z2 = lcg(n, 2);
        let ex = lcg(n, 3);
        let ey = lcg(n, 4);
        let x = (0..n).map(|i| 1.5 * z1[i] - z2[i] + ex[i]).collect();
        let y = (0..n)
            .map(|i| 0.5 + z1[i] + 2.0 * z2[i] + ex[i] * 0.3 + ey[i])
            .collect();
        (x, y, z1, z2)
    }

    fn ds(cs: Vec<(&str, ColumnKind, Vec<f64>)>) -> Dataset {
        Dataset::from_columns(
            cs.into_iter()
                .map(|(n, k, v)| (n.to_string(), k, v))
                .collect(),
        )
        .unwrap()
    }

    fn formula(rx: &[f64], ry: &[f64]) -> (f64, f64, f64) {
        let n = rx.len() as f64;
        let u: Vec<f64> = rx.iter().zip(ry).map(|(a, b)| a * b).collect();
        let m = u.iter().sum::<f64>() / n;
        let sd = (u.iter().map(|v| (v - m).powi(2)).sum::<f64>() / n).sqrt();
        let t = u.iter().sum::<f64>() / (n.sqrt() * sd);
        let p = 2.0 * Normal::new(0.0, 1.0).unwrap().sf(t.abs());
        let mx = rx.iter().sum::<f64>() / n;
        let my = ry.iter().sum::<f64>() / n;
        let cov_xy: f64 = rx.iter().zip(ry).map(|(a, b)| (a - mx) * (b - my)).sum();
        let var_x: f64 = rx.iter().map(|a| (a - mx).powi(2)).sum();
        let var_y: f64 = ry.iter().map(|b| (b - my).powi(2)).sum();
        (t, p, (cov_xy / (var_x.sqrt() * var_y.sqrt())).abs())
    }

    fn center(v: &[f64]) -> Vec<f64> {
        let m = v.iter().sum::<f64>() / v.len() as f64;
        v.iter().map(|a| a - m).collect()
    }

    /// Residuals of `v` on `[1, z1, z2]` via explicit normal equations.
    fn normal_eq_residuals(v: &[f64], z1: &[f64], z2: &[f64]) -> Vec<f64> {
        let n = v.len();
        let rows: Vec<[f64; 3]> = (0..n).map(|i| [1.0, z1[i], z2[i]]).collect();
        let mut a = [[0.0f64; 4]; 3];
        for (r, &t) in rows.iter().zip(v) {
            for i in 0..3 {
                for j in 0..3 {
                    a[i][j] += r[i] * r[j];
                }
                a[i][3] += r[i] * t;
            }
        }
        for c in 0..3 {
            let p = (c..3)
                .max_by(|&i, &j| a[i][c].abs().total_cmp(&a[j][c].abs()))
                .unwrap();
            a.swap(c, p);
            for r in 0..3 {
                if r != c {
                    let f = a[r][c] / a[c][c];
                    for k in c..4 {
                        a[r][k] -= f * a[c][k];
                    }
                }
            }
        }
        let beta: Vec<f64> = (0..3).map(|i| a[i][3] / a[i][i]).collect();
        rows.iter()
            .zip(v)
            .map(|(r, &t)| t - (0..3).map(|i| beta[i] * r[i]).sum::<f64>())
            .collect()
    }

    #[test]
    fn unconditional_matches_closed_form() {
        let (x, y, _, _) = cols(40);
        let data = ds(vec![
            ("x", ColumnKind::Continuous, x.clone()),
            ("y", ColumnKind::Continuous, y.clone()),
        ]);
        let r = Gcm::new().test(&data, 0, 1, &[]).unwrap();
        let (t, p, e) = formula(&center(&x), &center(&y));
        assert!((r.statistic.unwrap() - t).abs() < 1e-12);
        assert!((r.p_value - p).abs() < 1e-12);
        assert!((r.effect_size.unwrap() - e).abs() < 1e-12);
        assert_eq!(r.dof, None);
    }

    #[test]
    fn conditional_uses_ols_residuals() {
        let (x, y, z1, z2) = cols(60);
        let data = ds(vec![
            ("x", ColumnKind::Continuous, x.clone()),
            ("y", ColumnKind::Continuous, y.clone()),
            ("z1", ColumnKind::Continuous, z1.clone()),
            ("z2", ColumnKind::Continuous, z2.clone()),
        ]);
        let r = Gcm::new().test(&data, 0, 1, &[2, 3]).unwrap();
        let rx = normal_eq_residuals(&x, &z1, &z2);
        let ry = normal_eq_residuals(&y, &z1, &z2);
        let (t, p, e) = formula(&rx, &ry);
        assert!((r.statistic.unwrap() - t).abs() < 1e-10);
        assert!((r.p_value - p).abs() < 1e-10);
        assert!((r.effect_size.unwrap() - e).abs() < 1e-10);
    }

    #[test]
    fn symmetric_in_x_and_y() {
        let (x, y, z1, _) = cols(50);
        let data = ds(vec![
            ("x", ColumnKind::Continuous, x),
            ("y", ColumnKind::Continuous, y),
            ("z", ColumnKind::Continuous, z1),
        ]);
        let a = Gcm::new().test(&data, 0, 1, &[2]).unwrap();
        let b = Gcm::new().test(&data, 1, 0, &[2]).unwrap();
        assert!((a.statistic.unwrap() - b.statistic.unwrap()).abs() < 1e-12);
        assert!((a.p_value - b.p_value).abs() < 1e-12);
        assert!((a.effect_size.unwrap() - b.effect_size.unwrap()).abs() < 1e-12);
    }

    #[test]
    fn discrete_column_is_wrong_kind() {
        let (x, y, z1, _) = cols(20);
        let codes: Vec<f64> = (0..20).map(|i| f64::from(i % 3)).collect();
        let d = ColumnKind::Discrete;
        let c = ColumnKind::Continuous;
        for (kx, ky, kz) in [(d, c, c), (c, d, c), (c, c, d)] {
            let data = ds(vec![
                ("x", kx, if kx == d { codes.clone() } else { x.clone() }),
                ("y", ky, if ky == d { codes.clone() } else { y.clone() }),
                ("z", kz, if kz == d { codes.clone() } else { z1.clone() }),
            ]);
            assert!(matches!(
                Gcm::new().test(&data, 0, 1, &[2]),
                Err(CiError::WrongColumnKind(_))
            ));
        }
    }

    #[test]
    fn x_determined_by_z_is_degenerate() {
        let (_, y, z1, _) = cols(30);
        let x: Vec<f64> = z1.iter().map(|v| 2.0 * v + 1.0).collect();
        let data = ds(vec![
            ("x", ColumnKind::Continuous, x),
            ("y", ColumnKind::Continuous, y),
            ("z", ColumnKind::Continuous, z1),
        ]);
        assert!(matches!(
            Gcm::new().test(&data, 0, 1, &[2]),
            Err(CiError::DegenerateData(_))
        ));
    }

    #[test]
    fn constant_x_or_y_is_degenerate() {
        let (x, y, z1, _) = cols(30);
        let k = vec![0.1; 30];
        for z in [vec![], vec![2usize]] {
            for (xs, ys) in [(k.clone(), y.clone()), (x.clone(), k.clone())] {
                let data = ds(vec![
                    ("x", ColumnKind::Continuous, xs),
                    ("y", ColumnKind::Continuous, ys),
                    ("z", ColumnKind::Continuous, z1.clone()),
                ]);
                assert!(matches!(
                    Gcm::new().test(&data, 0, 1, &z),
                    Err(CiError::DegenerateData(_))
                ));
            }
        }
    }

    #[test]
    fn negating_y_flips_statistic_sign() {
        let (x, y, _, _) = cols(40);
        let neg: Vec<f64> = y.iter().map(|v| -v).collect();
        let mk = |ys| {
            ds(vec![
                ("x", ColumnKind::Continuous, x.clone()),
                ("y", ColumnKind::Continuous, ys),
            ])
        };
        let a = Gcm::new().test(&mk(y), 0, 1, &[]).unwrap();
        let b = Gcm::new().test(&mk(neg), 0, 1, &[]).unwrap();
        assert!((a.statistic.unwrap() + b.statistic.unwrap()).abs() < 1e-12);
        assert!((a.p_value - b.p_value).abs() < 1e-12);
    }
}
