//! Pillai's-trace conditional-independence test (mixed discrete/continuous
//! data), after pgmpy's `PillaiTrace` with linear residualization.
//!
//! X and Y are linearly regressed on `[1, Z]` (a continuous variable gives one
//! residual column; a discrete variable with K levels gives K−1 columns, a
//! linear probability model). With residual blocks `R_x` (n × p) and `R_y`
//! (n × q), `s = min(p, q)`, Pillai's trace is
//! `V = Σ ρᵢ² = tr(S_xx⁻¹ S_xy S_yy⁻¹ S_yx)` over the canonical correlations,
//! computed exactly (no iterative CCA). The p-value uses pgmpy's
//! F-approximation, `df1 = p·q`, `df2 = s·(n − 1 + s − p − q)`,
//! `F = (V/df1)·(df2/(s − V))`, evaluated with the F survival function. The
//! effect size is `V/s`; the statistic is `V`.
//!
//! As in pgmpy, `df2` ignores the number of conditioning columns. When `n`
//! minus the number of design columns (`[1, Z]`) equals `max(p, q)` and `Z` is
//! not empty, the residuals force `V = s` and the test returns `p = 0`
//! ("dependent"), exactly as pgmpy does. When it is smaller than `max(p, q)`,
//! a residual block is singular and the test returns an error. Linearly
//! dependent conditioning columns (duplicate or nested categoricals, a constant
//! column) raise a degenerate-data error, whereas pgmpy fits them by least
//! squares.

use faer::{Mat, MatRef};
use statrs::distribution::{ContinuousCDF, FisherSnedecor};

use crate::dataset::Dataset;
use crate::error::CiError;
use crate::residual::{design_matrix, ols_residuals_multi, target_block};
use crate::strategy::{CITest, CiResult, DataType, IndependenceRule, TestMeta};

/// Relative threshold below which a residual column is treated as zero.
const RESIDUAL_TOL: f64 = 1e-10;
/// Smallest admissible squared Cholesky pivot of a unit-diagonal block.
const PIVOT_TOL: f64 = 1e-10;
/// `V` within this relative distance of `s` counts as perfect dependence.
const PERFECT_TOL: f64 = 1e-12;

/// Pillai's-trace test (linear residualization, mixed data).
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct Pillai;

impl Pillai {
    /// Construct the test (no configuration).
    #[must_use]
    pub fn new() -> Self {
        Self
    }
}

/// Residual block of `col` on `design`, with a check that no residual column
/// is (numerically) constant zero relative to its target column.
fn residual_block(data: &Dataset, design: &Mat<f64>, col: usize) -> Result<Mat<f64>, CiError> {
    let label = data
        .name_of(col)
        .map_or_else(|| col.to_string(), |n| format!("`{n}`"));
    if let Ok(values) = data.continuous(col) {
        let (lo, hi) = values
            .iter()
            .fold((f64::INFINITY, f64::NEG_INFINITY), |(l, h), &v| {
                (l.min(v), h.max(v))
            });
        if lo >= hi {
            return Err(CiError::DegenerateData(format!(
                "column {label} is constant"
            )));
        }
    }
    let target = target_block(data, col)?;
    let res = ols_residuals_multi(design.as_ref(), target.as_ref())?;
    let n = target.nrows();
    #[allow(clippy::cast_precision_loss)]
    let nf = n as f64;
    for j in 0..target.ncols() {
        let mean = (0..n).map(|i| target[(i, j)]).sum::<f64>() / nf;
        let scale: f64 = (0..n).map(|i| (target[(i, j)] - mean).powi(2)).sum();
        let max_abs = (0..n).fold(0.0_f64, |m, i| m.max(target[(i, j)].abs()));
        let res_ss: f64 = (0..n).map(|i| res[(i, j)].powi(2)).sum();
        let noise = nf * f64::EPSILON * f64::EPSILON * max_abs * max_abs;
        if !res_ss.is_finite() || res_ss <= RESIDUAL_TOL * RESIDUAL_TOL * scale + noise {
            return Err(CiError::DegenerateData(format!(
                "residual of column {label} given Z has no variance"
            )));
        }
    }
    Ok(res)
}

/// Column-centers `m` and scales every column to unit Euclidean norm.
fn standardize(m: MatRef<'_, f64>) -> Result<Mat<f64>, CiError> {
    let (n, k) = (m.nrows(), m.ncols());
    #[allow(clippy::cast_precision_loss)]
    let nf = n as f64;
    let mut out = Mat::zeros(n, k);
    for j in 0..k {
        let mean = (0..n).map(|i| m[(i, j)]).sum::<f64>() / nf;
        let norm = (0..n)
            .map(|i| (m[(i, j)] - mean).powi(2))
            .sum::<f64>()
            .sqrt();
        if !(norm.is_finite() && norm > 0.0) {
            return Err(CiError::DegenerateData(
                "residual column has no variance".to_string(),
            ));
        }
        for i in 0..n {
            out[(i, j)] = (m[(i, j)] - mean) / norm;
        }
    }
    Ok(out)
}

/// `aᵀ b` for two matrices with the same number of rows.
fn cross(a: MatRef<'_, f64>, b: MatRef<'_, f64>) -> Mat<f64> {
    Mat::from_fn(a.ncols(), b.ncols(), |i, j| {
        (0..a.nrows()).map(|r| a[(r, i)] * b[(r, j)]).sum()
    })
}

/// Lower Cholesky factor of a unit-diagonal correlation matrix; a pivot whose
/// square is not above [`PIVOT_TOL`] means the block is (numerically) singular.
#[allow(clippy::many_single_char_names)] // standard linear-algebra names
fn cholesky(c: &Mat<f64>) -> Result<Mat<f64>, CiError> {
    let k = c.nrows();
    let mut l = Mat::<f64>::zeros(k, k);
    for j in 0..k {
        let d = c[(j, j)] - (0..j).map(|t| l[(j, t)].powi(2)).sum::<f64>();
        if !(d.is_finite() && d > PIVOT_TOL) {
            return Err(CiError::DegenerateData(
                "residual block is singular (collinear or determined by Z)".to_string(),
            ));
        }
        let ljj = d.sqrt();
        l[(j, j)] = ljj;
        for i in j + 1..k {
            let s: f64 = (0..j).map(|t| l[(i, t)] * l[(j, t)]).sum();
            l[(i, j)] = (c[(i, j)] - s) / ljj;
        }
    }
    Ok(l)
}

/// Solves `L W = B` (forward substitution) for lower-triangular `L`.
fn forward_solve(l: &Mat<f64>, b: &Mat<f64>) -> Mat<f64> {
    let mut w = Mat::<f64>::zeros(b.nrows(), b.ncols());
    for c in 0..b.ncols() {
        for i in 0..b.nrows() {
            let s: f64 = (0..i).map(|t| l[(i, t)] * w[(t, c)]).sum();
            w[(i, c)] = (b[(i, c)] - s) / l[(i, i)];
        }
    }
    w
}

/// Pillai's trace `tr(S_xx⁻¹ S_xy S_yy⁻¹ S_yx)` of two residual blocks.
///
/// # Errors
///
/// Returns [`CiError::DegenerateData`] if either block is singular or a
/// column is constant, or [`CiError::DimensionMismatch`] on unequal row counts.
pub(crate) fn pillai_trace(rx: MatRef<'_, f64>, ry: MatRef<'_, f64>) -> Result<f64, CiError> {
    if rx.nrows() != ry.nrows() {
        return Err(CiError::DimensionMismatch(format!(
            "residual blocks have {} and {} rows",
            rx.nrows(),
            ry.nrows()
        )));
    }
    let ux = standardize(rx)?;
    let uy = standardize(ry)?;
    let lx = cholesky(&cross(ux.as_ref(), ux.as_ref()))?;
    let ly = cholesky(&cross(uy.as_ref(), uy.as_ref()))?;
    // M = Lx⁻¹ Cxy Ly⁻ᵀ ; V = ‖M‖_F². Compute Lx⁻¹ Cxy, then solve for Ly.
    let a = forward_solve(&lx, &cross(ux.as_ref(), uy.as_ref()));
    // Rows of `a` times Ly⁻ᵀ: solve Ly Wᵀ = aᵀ.
    let at = Mat::from_fn(a.ncols(), a.nrows(), |i, j| a[(j, i)]);
    let w = forward_solve(&ly, &at);
    let v: f64 = (0..w.nrows())
        .map(|i| (0..w.ncols()).map(|j| w[(i, j)].powi(2)).sum::<f64>())
        .sum();
    if !v.is_finite() {
        return Err(CiError::DegenerateData(
            "Pillai's trace is not finite".to_string(),
        ));
    }
    Ok(v)
}

#[allow(clippy::many_single_char_names, clippy::similar_names)] // x, y, z, n, p, q, s are the standard names
impl CITest for Pillai {
    fn test_impl(
        &self,
        data: &Dataset,
        x: usize,
        y: usize,
        z: &[usize],
    ) -> Result<CiResult, CiError> {
        let design = design_matrix(data, z)?;
        let rx = residual_block(data, &design, x)?;
        let ry = residual_block(data, &design, y)?;
        let (n, p, q) = (rx.nrows(), rx.ncols(), ry.ncols());
        let s = p.min(q);
        let v = pillai_trace(rx.as_ref(), ry.as_ref())?;

        #[allow(clippy::cast_precision_loss)]
        let (sf, df1, df2) = {
            let sf = s as f64;
            let df1 = (p * q) as f64;
            // pgmpy: df2 = s · (n − 1 + s − p − q), ignoring |Z|.
            let df2 = sf * ((n + s) as f64 - 1.0 - (p + q) as f64);
            (sf, df1, df2)
        };
        if df2.is_nan() || df2 <= 0.0 {
            return Err(CiError::DegenerateData(format!(
                "denominator degrees of freedom {df2} are not positive"
            )));
        }
        let v = v.min(sf);
        let p_value = if sf - v <= PERFECT_TOL * sf {
            0.0
        } else {
            let f_stat = (v / df1) * (df2 / (sf - v));
            let dist = FisherSnedecor::new(df1, df2)
                .map_err(|e| CiError::Numeric(format!("F distribution: {e}")))?;
            dist.sf(f_stat)
        };
        Ok(CiResult {
            statistic: Some(v),
            p_value,
            dof: None,
            effect_size: Some(v / sf),
        })
    }

    fn meta(&self) -> TestMeta {
        TestMeta {
            name: "pillai",
            data_types: &[DataType::Discrete, DataType::Continuous],
            symmetric: true,
            rule: IndependenceRule::PValueGe,
        }
    }
}

#[cfg(test)]
#[allow(
    clippy::cast_possible_truncation,
    clippy::cast_precision_loss,
    clippy::cast_sign_loss,
    clippy::float_cmp,
    clippy::many_single_char_names,
    clippy::similar_names,
    clippy::unreadable_literal
)] // test helpers: small n, explicit math
mod tests {
    use super::*;
    use crate::ci_tests::PearsonCorrelation;
    use crate::dataset::ColumnKind;

    fn lcg(n: usize, seed: u64) -> Vec<f64> {
        let mut s = seed;
        (0..n)
            .map(|_| {
                s = s
                    .wrapping_mul(6364136223846793005)
                    .wrapping_add(1442695040888963407);
                let v = (s >> 11) as f64 / (1u64 << 53) as f64;
                v - 0.5
            })
            .collect()
    }

    fn ds(cs: Vec<(&str, ColumnKind, Vec<f64>)>) -> Dataset {
        Dataset::from_columns(
            cs.into_iter()
                .map(|(n, k, v)| (n.to_string(), k, v))
                .collect(),
        )
        .unwrap()
    }

    fn levels(u: &[f64], k: usize) -> Vec<f64> {
        u.iter()
            .map(|v| (((v + 0.5) * k as f64) as usize).min(k - 1) as f64)
            .collect()
    }

    #[test]
    fn continuous_pair_matches_squared_pearson() {
        let n = 50;
        let (e, f) = (lcg(n, 1), lcg(n, 2));
        let x = e.clone();
        let y: Vec<f64> = (0..n).map(|i| 0.6 * e[i] + f[i]).collect();
        let data = ds(vec![
            ("x", ColumnKind::Continuous, x.clone()),
            ("y", ColumnKind::Continuous, y.clone()),
        ]);
        let r = Pillai::new().test(&data, 0, 1, &[]).unwrap();
        let mx = x.iter().sum::<f64>() / n as f64;
        let my = y.iter().sum::<f64>() / n as f64;
        let sxy: f64 = (0..n).map(|i| (x[i] - mx) * (y[i] - my)).sum();
        let sxx: f64 = x.iter().map(|a| (a - mx).powi(2)).sum();
        let syy: f64 = y.iter().map(|a| (a - my).powi(2)).sum();
        let r2 = sxy * sxy / (sxx * syy);
        assert!((r.statistic.unwrap() - r2).abs() < 1e-12);
        assert!((r.effect_size.unwrap() - r2).abs() < 1e-12);
        let pc = PearsonCorrelation::new().test(&data, 0, 1, &[]).unwrap();
        assert!((r.p_value - pc.p_value).abs() < 1e-10);
        assert_eq!(r.dof, None);
    }

    #[test]
    fn categorical_vs_continuous_is_one_way_anova() {
        let n = 60;
        let k = 3;
        let x = levels(&lcg(n, 5), k);
        let noise = lcg(n, 6);
        let y: Vec<f64> = (0..n).map(|i| 0.4 * x[i] + noise[i]).collect();
        let data = ds(vec![
            ("x", ColumnKind::Discrete, x.clone()),
            ("y", ColumnKind::Continuous, y.clone()),
        ]);
        let r = Pillai::new().test(&data, 0, 1, &[]).unwrap();
        let grand = y.iter().sum::<f64>() / n as f64;
        let (mut ssb, mut ssw) = (0.0, 0.0);
        for g in 0..k {
            let ys: Vec<f64> = (0..n)
                .filter(|&i| x[i] as usize == g)
                .map(|i| y[i])
                .collect();
            let m = ys.iter().sum::<f64>() / ys.len() as f64;
            ssb += ys.len() as f64 * (m - grand).powi(2);
            ssw += ys.iter().map(|v| (v - m).powi(2)).sum::<f64>();
        }
        let v = ssb / (ssb + ssw);
        assert!((r.statistic.unwrap() - v).abs() < 1e-12);
        let f_anova = (ssb / (k - 1) as f64) / (ssw / (n - k) as f64);
        let p = FisherSnedecor::new((k - 1) as f64, (n - k) as f64)
            .unwrap()
            .sf(f_anova);
        assert!((r.p_value - p).abs() < 1e-10);
    }

    #[test]
    fn mixed_conditioning_runs_and_is_symmetric() {
        let n = 120;
        let x = levels(&lcg(n, 7), 3);
        let zd = levels(&lcg(n, 8), 2);
        let zc = lcg(n, 9);
        let e = lcg(n, 10);
        let y: Vec<f64> = (0..n).map(|i| 0.3 * x[i] + zd[i] - zc[i] + e[i]).collect();
        let data = ds(vec![
            ("x", ColumnKind::Discrete, x),
            ("y", ColumnKind::Continuous, y),
            ("zd", ColumnKind::Discrete, zd),
            ("zc", ColumnKind::Continuous, zc),
        ]);
        let a = Pillai::new().test(&data, 0, 1, &[2, 3]).unwrap();
        let b = Pillai::new().test(&data, 1, 0, &[2, 3]).unwrap();
        assert!(a.p_value.is_finite() && (0.0..=1.0).contains(&a.p_value));
        assert!((a.statistic.unwrap() - b.statistic.unwrap()).abs() < 1e-12);
        assert!((a.p_value - b.p_value).abs() < 1e-12);
    }

    #[test]
    fn perfect_dependence_gives_p_zero() {
        let n = 40;
        let x = lcg(n, 11);
        let data = ds(vec![
            ("x", ColumnKind::Continuous, x.clone()),
            ("y", ColumnKind::Continuous, x),
        ]);
        let r = Pillai::new().test(&data, 0, 1, &[]).unwrap();
        assert!((r.statistic.unwrap() - 1.0).abs() < 1e-12);
        assert_eq!(r.p_value, 0.0);

        let cx = levels(&lcg(n, 12), 3);
        let cy: Vec<f64> = cx.iter().map(|v| (v + 1.0) % 3.0).collect();
        let data = ds(vec![
            ("x", ColumnKind::Discrete, cx),
            ("y", ColumnKind::Discrete, cy),
        ]);
        let r = Pillai::new().test(&data, 0, 1, &[]).unwrap();
        assert!((r.statistic.unwrap() - 2.0).abs() < 1e-12);
        assert!(r.statistic.unwrap().is_finite());
        assert_eq!(r.p_value, 0.0);
    }

    #[test]
    fn categorical_x_determined_by_z_is_degenerate() {
        let n = 60;
        let zd = levels(&lcg(n, 13), 3);
        let x: Vec<f64> = zd.iter().map(|v| (v + 1.0) % 3.0).collect();
        let y = lcg(n, 14);
        let data = ds(vec![
            ("x", ColumnKind::Discrete, x),
            ("y", ColumnKind::Continuous, y),
            ("z", ColumnKind::Discrete, zd),
        ]);
        assert!(matches!(
            Pillai::new().test(&data, 0, 1, &[2]),
            Err(CiError::DegenerateData(_))
        ));
    }

    #[test]
    fn constant_continuous_x_or_y_is_degenerate() {
        let n = 50;
        let (a, b) = (lcg(n, 21), lcg(n, 22));
        for c in [0.1, 1.0, 3.7] {
            for z in [vec![], vec![2usize]] {
                for const_is_y in [true, false] {
                    let k = vec![c; n];
                    let (xs, ys) = if const_is_y {
                        (a.clone(), k)
                    } else {
                        (k, a.clone())
                    };
                    let data = ds(vec![
                        ("x", ColumnKind::Continuous, xs),
                        ("y", ColumnKind::Continuous, ys),
                        ("z", ColumnKind::Continuous, b.clone()),
                    ]);
                    assert!(
                        matches!(
                            Pillai::new().test(&data, 0, 1, &z),
                            Err(CiError::DegenerateData(_))
                        ),
                        "c={c} z={z:?} const_is_y={const_is_y}"
                    );
                }
            }
        }
    }

    #[test]
    fn f_tail_is_accurate() {
        let p = FisherSnedecor::new(3.0, 200.0).unwrap().sf(40.0);
        let expected = 2.7079201317013815e-20;
        assert!(((p - expected) / expected).abs() < 1e-9, "{p}");
    }

    fn scaled_data(n: usize, scales: &[f64]) -> Dataset {
        let z1 = lcg(n, 11);
        let z2 = lcg(n, 12);
        let x: Vec<f64> = (0..n).map(|i| z1[i] + lcg(n, 13)[i]).collect();
        let y: Vec<f64> = (0..n).map(|i| z1[i] - z2[i] + lcg(n, 14)[i]).collect();
        let (s1, s2) = (scales[0], scales[1]);
        ds(vec![
            ("x", ColumnKind::Continuous, x),
            ("y", ColumnKind::Continuous, y),
            (
                "z1",
                ColumnKind::Continuous,
                z1.iter().map(|v| v * s1).collect(),
            ),
            (
                "z2",
                ColumnKind::Continuous,
                z2.iter().map(|v| v * s2).collect(),
            ),
        ])
    }

    #[test]
    fn conditioning_scale_does_not_change_results() {
        use crate::ci_tests::Gcm;
        let base = scaled_data(60, &[1.0, 1.0]);
        let pb = Pillai::new().test(&base, 0, 1, &[2, 3]).unwrap();
        let gb = Gcm::new().test(&base, 0, 1, &[2, 3]).unwrap();
        for sc in [[1e12, 1e12], [1e-12, 1e-12], [1e6, 1e-5], [1e11, 1.0]] {
            let d = scaled_data(60, &sc);
            let p = Pillai::new().test(&d, 0, 1, &[2, 3]).unwrap();
            let g = Gcm::new().test(&d, 0, 1, &[2, 3]).unwrap();
            let rel = |a: f64, b: f64| (a - b).abs() / b.abs().max(1e-300);
            assert!(
                rel(p.statistic.unwrap(), pb.statistic.unwrap()) < 1e-9,
                "{sc:?}"
            );
            assert!(rel(p.p_value, pb.p_value) < 1e-9, "{sc:?}");
            assert!(
                rel(g.statistic.unwrap(), gb.statistic.unwrap()) < 1e-9,
                "{sc:?}"
            );
            assert!(rel(g.p_value, gb.p_value) < 1e-9, "{sc:?}");
        }
    }

    #[test]
    fn constant_or_duplicated_z_still_rejected_and_tiny_variance_target_accepted() {
        use crate::ci_tests::Gcm;
        let n = 40;
        let (x, y, z) = (lcg(n, 21), lcg(n, 22), lcg(n, 23));
        let cd = |extra: Vec<f64>| {
            ds(vec![
                ("x", ColumnKind::Continuous, x.clone()),
                ("y", ColumnKind::Continuous, y.clone()),
                ("z", ColumnKind::Continuous, z.clone()),
                ("w", ColumnKind::Continuous, extra),
            ])
        };
        for scale in [1.0, 1e12, 1e-12] {
            for extra in [vec![scale; n], z.iter().map(|v| v * scale).collect()] {
                let d = cd(extra);
                assert!(matches!(
                    Pillai::new().test(&d, 0, 1, &[2, 3]),
                    Err(CiError::DegenerateData(_))
                ));
                assert!(matches!(
                    Gcm::new().test(&d, 0, 1, &[2, 3]),
                    Err(CiError::DegenerateData(_))
                ));
            }
        }
        let xs: Vec<f64> = x.iter().map(|v| 1.0 + 1e-9 * v).collect();
        let d = ds(vec![
            ("x", ColumnKind::Continuous, xs),
            ("y", ColumnKind::Continuous, y.clone()),
            ("z", ColumnKind::Continuous, z.clone()),
        ]);
        assert!(Pillai::new().test(&d, 0, 1, &[2]).is_ok());
        assert!(Gcm::new().test(&d, 0, 1, &[2]).is_ok());
    }

    #[test]
    fn errors_use_column_names() {
        let n = 30;
        let (y, z) = (lcg(n, 31), lcg(n, 32));
        let d = ds(vec![
            ("alpha", ColumnKind::Continuous, vec![0.5; n]),
            ("beta", ColumnKind::Continuous, y.clone()),
            ("z", ColumnKind::Continuous, z.clone()),
        ]);
        let msg = Pillai::new().test(&d, 0, 1, &[]).unwrap_err().to_string();
        assert!(msg.contains("alpha"), "{msg}");
        let x: Vec<f64> = z.iter().map(|v| 2.0 * v + 1.0).collect();
        let d = ds(vec![
            ("alpha", ColumnKind::Continuous, x),
            ("beta", ColumnKind::Continuous, y),
            ("z", ColumnKind::Continuous, z),
        ]);
        let msg = Pillai::new().test(&d, 0, 1, &[2]).unwrap_err().to_string();
        assert!(msg.contains("alpha"), "{msg}");
    }
}
