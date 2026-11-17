//! Hilbert-Schmidt independence criterion (HSIC) test for two continuous
//! variables, matching pgmpy's `HSIC` (gamma null) with an additional
//! deterministic permutation null.

use faer::Mat;

use crate::dataset::Dataset;
use crate::error::CIError;
use crate::kernel::{
    center, dense_len_guard, gamma_pvalue, kernel_matrix, median_length_scale, standardized,
    Bandwidth, Kernel, KernelChoice,
};
use crate::rng::{shuffle_identity, SplitMix64};
use crate::strategy::{CIResult, CITest, DataType, IndependenceRule, TestMeta};

/// How the null distribution of the HSIC statistic is approximated.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum NullDistribution {
    /// Gamma approximation from the null moments (fast).
    #[default]
    Gamma,
    /// Monte-Carlo permutation null, reproducible from `seed`.
    Permutation {
        /// Number of permutations; must be at least 1.
        n_permutations: usize,
        /// Seed of the deterministic permutation stream.
        seed: u64,
    },
}

/// HSIC independence test (`X ⊥ Y`, no conditioning set).
#[derive(Debug, Clone, PartialEq, Default)]
pub struct Hsic {
    /// Kernel selection.
    pub kernel: KernelChoice,
    /// Bandwidth rule for default RBF kernels.
    pub bandwidth: Bandwidth,
    /// Null-distribution approximation.
    pub null_dist: NullDistribution,
}

impl Hsic {
    /// pgmpy defaults: default kernels, heuristic bandwidth, gamma null.
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }
}

/// Default per-column RBF length scale by sample size.
#[must_use]
pub(crate) fn hsic_heuristic_length_scale(n: usize) -> f64 {
    if n < 200 {
        0.8
    } else if n < 1200 {
        0.5
    } else {
        0.3
    }
}

/// Kernel for one column under `choice`, with the default RBF as fallback.
fn column_kernel(
    data: &Dataset,
    col: usize,
    points: &Mat<f64>,
    choice: &KernelChoice,
    bandwidth: Bandwidth,
) -> Kernel {
    let explicit = match choice {
        KernelChoice::Auto => None,
        KernelChoice::All(k) => Some(*k),
        KernelChoice::PerColumn(map) => data.name_of(col).and_then(|n| map.get(n)).copied(),
    };
    explicit.unwrap_or_else(|| Kernel::Rbf {
        length_scale: match bandwidth {
            Bandwidth::Heuristic => hsic_heuristic_length_scale(points.nrows()),
            Bandwidth::Median => median_length_scale(points.as_ref()),
        },
    })
}

/// Frobenius inner product of two equally sized matrices.
fn inner(a: &Mat<f64>, b: &Mat<f64>) -> f64 {
    let mut s = 0.0;
    for j in 0..a.ncols() {
        for i in 0..a.nrows() {
            s += a[(i, j)] * b[(i, j)];
        }
    }
    s
}

/// Unconditional HSIC of columns `x` and `y`; also KCI's empty-Z fallback.
pub(crate) fn hsic_unconditional(
    data: &Dataset,
    x: usize,
    y: usize,
    kernel: &KernelChoice,
    bandwidth: Bandwidth,
    null_dist: NullDistribution,
) -> Result<CIResult, CIError> {
    let n = data.n_rows();
    dense_len_guard(n)?;
    let px = standardized(data, &[x], 1.0)?;
    let py = standardized(data, &[y], 1.0)?;
    let kernel_x = column_kernel(data, x, &px, kernel, bandwidth);
    let kernel_y = column_kernel(data, y, &py, kernel, bandwidth);
    let mut kx = kernel_matrix(kernel_x, px.as_ref());
    let mut ky = kernel_matrix(kernel_y, py.as_ref());

    // Uncentered moments needed by the gamma null.
    let (sum_x, tr_x) = sum_and_trace(&kx);
    let (sum_y, tr_y) = sum_and_trace(&ky);
    center(&mut kx);
    center(&mut ky);

    let stat = inner(&kx, &ky);
    let denom = (inner(&kx, &kx) * inner(&ky, &ky)).sqrt();
    let effect = if denom > 0.0 { stat / denom } else { 0.0 };

    #[allow(clippy::cast_precision_loss)]
    let p_value = match null_dist {
        NullDistribution::Permutation {
            n_permutations,
            seed,
        } => {
            let mut rng = SplitMix64::new(seed);
            let mut perm = vec![0usize; n];
            let mut count = 0usize;
            for _ in 0..n_permutations {
                shuffle_identity(&mut rng, &mut perm);
                let mut s = 0.0;
                for j in 0..n {
                    for i in 0..n {
                        s += kx[(i, j)] * ky[(perm[i], perm[j])];
                    }
                }
                if s >= stat {
                    count += 1;
                }
            }
            (1 + count) as f64 / (1 + n_permutations) as f64
        }
        NullDistribution::Gamma => {
            if n < 6 {
                1.0
            } else {
                let nf = n as f64;
                let n_pairs = nf * (nf - 1.0);
                let mut pp = 0.0;
                let mut diag_sq = 0.0;
                for j in 0..n {
                    for i in 0..n {
                        let v = kx[(i, j)] * ky[(i, j)];
                        pp += v * v;
                        if i == j {
                            diag_sq += v * v;
                        }
                    }
                }
                let off = (pp - diag_sq) / 36.0;
                let factor = 72.0 * (nf - 4.0) * (nf - 5.0) / (n_pairs * (nf - 2.0) * (nf - 3.0));
                let var = factor * off / n_pairs;
                let mu_x = (sum_x - tr_x) / n_pairs;
                let mu_y = (sum_y - tr_y) / n_pairs;
                let mean = (tr_x / nf - mu_x) * (tr_y / nf - mu_y) / nf;
                gamma_pvalue(stat / nf, nf * mean, nf * nf * var)?
            }
        }
    };

    Ok(CIResult {
        statistic: Some(stat),
        p_value,
        dof: None,
        effect_size: Some(effect),
    })
}

/// Sum of all entries and trace of a square matrix.
fn sum_and_trace(k: &Mat<f64>) -> (f64, f64) {
    let mut sum = 0.0;
    let mut tr = 0.0;
    for j in 0..k.ncols() {
        for i in 0..k.nrows() {
            sum += k[(i, j)];
        }
        tr += k[(j, j)];
    }
    (sum, tr)
}

impl CITest for Hsic {
    fn validate(&self, data: &Dataset) -> Result<(), CIError> {
        if let NullDistribution::Permutation { n_permutations, .. } = self.null_dist {
            if n_permutations < 1 {
                return Err(CIError::InvalidConfig(
                    "n_permutations must be >= 1".to_string(),
                ));
            }
        }
        self.kernel.validate(data)
    }

    fn test_impl(
        &self,
        data: &Dataset,
        x: usize,
        y: usize,
        z: &[usize],
    ) -> Result<CIResult, CIError> {
        if !z.is_empty() {
            return Err(CIError::InvalidQuery(
                "HSIC does not support a conditioning set; use KCI".to_string(),
            ));
        }
        hsic_unconditional(data, x, y, &self.kernel, self.bandwidth, self.null_dist)
    }

    fn meta(&self) -> TestMeta {
        TestMeta {
            name: "hsic",
            data_types: &[DataType::Continuous],
            symmetric: true,
            rule: IndependenceRule::PValueGe,
        }
    }
}

#[cfg(test)]
#[allow(
    clippy::float_cmp,
    clippy::cast_precision_loss,
    clippy::many_single_char_names,
    clippy::similar_names
)]
mod tests {
    use super::*;
    use crate::dataset::{ColumnKind, Dataset};
    use crate::error::CIError;
    use crate::kernel::{Bandwidth, Kernel, KernelChoice};
    use crate::rng::SplitMix64;
    use crate::strategy::CITest;
    use std::collections::BTreeMap;

    fn uniform(rng: &mut SplitMix64) -> f64 {
        ((rng.next_u64() >> 11) as f64 + 0.5) / (1u64 << 53) as f64
    }

    fn normals(rng: &mut SplitMix64, n: usize) -> Vec<f64> {
        let mut out = Vec::with_capacity(n);
        while out.len() < n {
            let (u1, u2) = (uniform(rng), uniform(rng));
            let r = (-2.0 * u1.ln()).sqrt();
            out.push(r * (2.0 * std::f64::consts::PI * u2).cos());
            out.push(r * (2.0 * std::f64::consts::PI * u2).sin());
        }
        out.truncate(n);
        out
    }

    fn ds(cols: Vec<(&str, ColumnKind, Vec<f64>)>) -> Dataset {
        Dataset::from_columns(
            cols.into_iter()
                .map(|(n, k, v)| (n.to_string(), k, v))
                .collect(),
        )
        .unwrap()
    }

    fn two(x: Vec<f64>, y: Vec<f64>) -> Dataset {
        ds(vec![
            ("x", ColumnKind::Continuous, x),
            ("y", ColumnKind::Continuous, y),
        ])
    }

    fn pearson(x: &[f64], y: &[f64]) -> f64 {
        let n = x.len() as f64;
        let mx = x.iter().sum::<f64>() / n;
        let my = y.iter().sum::<f64>() / n;
        let sxy: f64 = x.iter().zip(y).map(|(a, b)| (a - mx) * (b - my)).sum();
        let sxx: f64 = x.iter().map(|a| (a - mx) * (a - mx)).sum();
        let syy: f64 = y.iter().map(|b| (b - my) * (b - my)).sum();
        sxy / (sxx * syy).sqrt()
    }

    fn rel(a: f64, b: f64) -> f64 {
        (a - b).abs() / b.abs().max(1e-300)
    }

    fn indep(n: usize, seed: u64) -> Dataset {
        let mut rng = SplitMix64::new(seed);
        two(normals(&mut rng, n), normals(&mut rng, n))
    }

    #[test]
    fn linear_kernel_matches_closed_form() {
        let mut rng = SplitMix64::new(1);
        let x = normals(&mut rng, 50);
        let e = normals(&mut rng, 50);
        let y: Vec<f64> = x.iter().zip(&e).map(|(a, b)| 0.5 * a + b).collect();
        let r = pearson(&x, &y);
        let d = two(x, y);
        let t = Hsic {
            kernel: KernelChoice::All(Kernel::Linear),
            ..Hsic::new()
        };
        let res = t.test(&d, 0, 1, &[]).unwrap();
        assert!(rel(res.statistic.unwrap(), (49.0 * r) * (49.0 * r)) < 1e-12);
        assert!(rel(res.effect_size.unwrap(), r * r) < 1e-12);
        assert_eq!(res.dof, None);
    }

    #[test]
    fn heuristic_length_scale_bands() {
        for n in [5, 199] {
            assert_eq!(hsic_heuristic_length_scale(n), 0.8);
        }
        for n in [200, 1199] {
            assert_eq!(hsic_heuristic_length_scale(n), 0.5);
        }
        for n in [1200, 5000] {
            assert_eq!(hsic_heuristic_length_scale(n), 0.3);
        }
    }

    #[test]
    fn tiny_sample_gamma_p_is_one() {
        let d = two(vec![1., 2., 3., 4., 5.], vec![2., 1., 4., 3., 7.]);
        let res = Hsic::new().test(&d, 0, 1, &[]).unwrap();
        assert_eq!(res.p_value, 1.0);
        assert!(res.statistic.unwrap().is_finite());
    }

    #[test]
    fn symmetric_in_x_and_y() {
        let d = indep(40, 3);
        let a = Hsic::new().test(&d, 0, 1, &[]).unwrap();
        let b = Hsic::new().test(&d, 1, 0, &[]).unwrap();
        assert!(rel(a.statistic.unwrap(), b.statistic.unwrap()) < 1e-12);
        assert!((a.p_value - b.p_value).abs() < 1e-12);
        assert!(rel(a.effect_size.unwrap(), b.effect_size.unwrap()) < 1e-12);
    }

    #[test]
    fn permutation_p_value_bounds_and_determinism() {
        let t = Hsic {
            null_dist: NullDistribution::Permutation {
                n_permutations: 19,
                seed: 7,
            },
            ..Hsic::new()
        };
        let d = indep(100, 11);
        let p = t.test(&d, 0, 1, &[]).unwrap().p_value;
        let k = p * 20.0;
        assert!((k - k.round()).abs() < 1e-9 && (1.0..=20.0).contains(&k.round()));
        assert_eq!(p, t.test(&d, 0, 1, &[]).unwrap().p_value);
        assert!(p > 0.05, "{p}");

        let mut rng = SplitMix64::new(5);
        let x = normals(&mut rng, 100);
        let e = normals(&mut rng, 100);
        let y: Vec<f64> = x.iter().zip(&e).map(|(a, b)| a * a + 0.01 * b).collect();
        let p = t.test(&two(x, y), 0, 1, &[]).unwrap().p_value;
        assert_eq!(p, 1.0 / 20.0);
    }

    #[test]
    fn rejects_conditioning_set() {
        let mut rng = SplitMix64::new(2);
        let d = ds(vec![
            ("x", ColumnKind::Continuous, normals(&mut rng, 30)),
            ("y", ColumnKind::Continuous, normals(&mut rng, 30)),
            ("z", ColumnKind::Continuous, normals(&mut rng, 30)),
        ]);
        assert!(matches!(
            Hsic::new().test(&d, 0, 1, &[2]),
            Err(CIError::InvalidQuery(_))
        ));
    }

    #[test]
    fn rejects_invalid_config() {
        let d = indep(30, 4);
        let t = Hsic {
            null_dist: NullDistribution::Permutation {
                n_permutations: 0,
                seed: 0,
            },
            ..Hsic::new()
        };
        assert!(matches!(t.validate(&d), Err(CIError::InvalidConfig(_))));
        assert!(matches!(
            t.test(&d, 0, 1, &[]),
            Err(CIError::InvalidConfig(_))
        ));
        for ell in [0.0, -1.0, f64::NAN] {
            let t = Hsic {
                kernel: KernelChoice::All(Kernel::Rbf { length_scale: ell }),
                ..Hsic::new()
            };
            assert!(matches!(t.validate(&d), Err(CIError::InvalidConfig(_))));
        }
        let mut m = BTreeMap::new();
        m.insert("nope".to_string(), Kernel::Linear);
        let t = Hsic {
            kernel: KernelChoice::PerColumn(m),
            ..Hsic::new()
        };
        assert!(matches!(t.validate(&d), Err(CIError::UnknownColumn(_))));
    }

    #[test]
    fn works_with_unrelated_discrete_columns() {
        let mut rng = SplitMix64::new(9);
        let d = ds(vec![
            ("x", ColumnKind::Continuous, normals(&mut rng, 20)),
            ("y", ColumnKind::Continuous, normals(&mut rng, 20)),
            (
                "d",
                ColumnKind::Discrete,
                (0..20).map(|i| f64::from(i % 3)).collect(),
            ),
        ]);
        assert!(Hsic::new().test(&d, 0, 1, &[]).is_ok());
    }

    #[test]
    fn perfectly_dependent_is_finite() {
        let mut rng = SplitMix64::new(13);
        let x = normals(&mut rng, 200);
        let y: Vec<f64> = x.iter().map(|a| 2.0 * a).collect();
        let res = Hsic::new().test(&two(x, y), 0, 1, &[]).unwrap();
        assert!(res.statistic.unwrap().is_finite());
        assert!(res.p_value < 1e-6, "{}", res.p_value);
    }

    #[test]
    fn dependent_vs_independent_gamma() {
        let mut rng = SplitMix64::new(21);
        let x = normals(&mut rng, 300);
        let e = normals(&mut rng, 300);
        let y: Vec<f64> = x
            .iter()
            .zip(&e)
            .map(|(a, b)| (3.0 * a).sin() + 0.1 * b)
            .collect();
        let p = Hsic::new().test(&two(x, y), 0, 1, &[]).unwrap().p_value;
        assert!(p < 1e-6, "{p}");
        let p = Hsic::new()
            .test(&indep(300, 22), 0, 1, &[])
            .unwrap()
            .p_value;
        assert!(p > 0.01, "{p}");
        let t = Hsic {
            bandwidth: Bandwidth::Median,
            ..Hsic::new()
        };
        assert!(t.test(&indep(300, 22), 0, 1, &[]).unwrap().p_value > 0.01);
    }
}
