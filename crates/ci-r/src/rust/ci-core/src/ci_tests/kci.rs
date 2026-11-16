//! Kernel conditional-independence (KCI) test for continuous variables,
//! matching pgmpy's `KCI` (gamma null from the eigenvalues of the
//! Z-residualized kernels). With an empty conditioning set it reduces to
//! [`Hsic`](crate::ci_tests::Hsic) with a gamma null.
//!
//! Cost: O(n²) memory and O(n³) time, as in pgmpy.

use faer::linalg::solvers::DenseSolveCore;
use faer::{Mat, Side};

use crate::ci_tests::hsic::{hsic_unconditional, NullDistribution};
use crate::dataset::Dataset;
use crate::error::CiError;
use crate::kernel::{
    center, dense_len_guard, gamma_pvalue, kernel_matrix, median_length_scale, standardized,
    Bandwidth, Kernel, KernelChoice,
};
use crate::strategy::{CITest, CiResult, DataType, IndependenceRule, TestMeta};

/// Eigenvalue cut-off relative to the largest eigenvalue.
const EIGEN_RELATIVE_CUTOFF: f64 = 1e-5;

/// KCI conditional-independence test (`X ⊥ Y | Z`).
#[derive(Debug, Clone, PartialEq)]
pub struct Kci {
    /// Kernel selection.
    pub kernel: KernelChoice,
    /// Bandwidth rule for default RBF kernels.
    pub bandwidth: Bandwidth,
    /// Ridge regularization `ε` of the Z-residualizer; finite and > 0.
    pub epsilon: f64,
}

impl Kci {
    /// pgmpy defaults: default kernels, heuristic bandwidth, `epsilon = 1e-3`.
    #[must_use]
    pub fn new() -> Self {
        Self {
            kernel: KernelChoice::default(),
            bandwidth: Bandwidth::default(),
            epsilon: 1e-3,
        }
    }
}

impl Default for Kci {
    fn default() -> Self {
        Self::new()
    }
}

/// Default RBF length scale `w · sqrt(|Z|)` by sample size.
#[must_use]
pub(crate) fn kci_heuristic_length_scale(n: usize, n_z: usize) -> f64 {
    let w = if n < 200 {
        1.2
    } else if n < 1200 {
        0.7
    } else {
        0.4
    };
    #[allow(clippy::cast_precision_loss)]
    let root = (n_z as f64).sqrt();
    w * root
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

fn numeric<E: std::fmt::Debug>(what: &str, e: E) -> CiError {
    CiError::Numeric(format!("{what} failed: {e:?}"))
}

/// Default RBF kernel for `points` under the bandwidth rule.
fn default_rbf(points: &Mat<f64>, bandwidth: Bandwidth, n: usize, n_z: usize) -> Kernel {
    Kernel::Rbf {
        length_scale: match bandwidth {
            Bandwidth::Heuristic => kci_heuristic_length_scale(n, n_z),
            Bandwidth::Median => median_length_scale(points.as_ref()),
        },
    }
}

/// Kernel for a queried column (X or Y) under `choice`.
fn queried_kernel(data: &Dataset, col: usize, points: &Mat<f64>, test: &Kci, n_z: usize) -> Kernel {
    let explicit = match &test.kernel {
        KernelChoice::Auto => None,
        KernelChoice::All(k) => Some(*k),
        KernelChoice::PerColumn(map) => data.name_of(col).and_then(|n| map.get(n)).copied(),
    };
    explicit.unwrap_or_else(|| default_rbf(points, test.bandwidth, points.nrows(), n_z))
}

/// Centered kernel matrix of `points`.
fn centered_kernel(kernel: Kernel, points: &Mat<f64>) -> Mat<f64> {
    let mut k = kernel_matrix(kernel, points.as_ref());
    center(&mut k);
    k
}

/// Kept eigenvectors scaled by `sqrt(eigenvalue)` of `½(A + Aᵀ)`.
fn scaled_eigenvectors(a: &Mat<f64>) -> Result<Mat<f64>, CiError> {
    let n = a.nrows();
    let sym = Mat::<f64>::from_fn(n, n, |i, j| 0.5 * (a[(i, j)] + a[(j, i)]));
    let eig = sym
        .self_adjoint_eigen(Side::Lower)
        .map_err(|e| numeric("eigendecomposition", e))?;
    let (values, vectors) = (eig.S(), eig.U());
    let w: Vec<f64> = (0..n).map(|i| values[i]).collect();
    let max = w.iter().copied().fold(f64::NEG_INFINITY, f64::max);
    let keep: Vec<usize> = (0..n)
        .filter(|&i| w[i] > max * EIGEN_RELATIVE_CUTOFF)
        .collect();
    Ok(Mat::<f64>::from_fn(n, keep.len(), |i, c| {
        vectors[(i, keep[c])] * w[keep[c]].sqrt()
    }))
}

impl CITest for Kci {
    fn validate(&self, data: &Dataset) -> Result<(), CiError> {
        if !(self.epsilon.is_finite() && self.epsilon > 0.0) {
            return Err(CiError::InvalidConfig(
                "epsilon must be finite and > 0".to_string(),
            ));
        }
        self.kernel.validate(data)
    }

    #[allow(
        clippy::many_single_char_names,
        clippy::similar_names,
        reason = "mirrors the x/y/z and kx/ky/kz notation of the spec"
    )]
    fn test_impl(
        &self,
        data: &Dataset,
        x: usize,
        y: usize,
        z: &[usize],
    ) -> Result<CiResult, CiError> {
        if z.is_empty() {
            return hsic_unconditional(
                data,
                x,
                y,
                &self.kernel,
                self.bandwidth,
                NullDistribution::Gamma,
            );
        }
        let n = data.n_rows();
        dense_len_guard(n)?;
        let n_z = z.len();

        let px = standardized(data, &[x], 1.0)?;
        let pz_half = standardized(data, z, 0.5)?;
        let py = standardized(data, &[y], 1.0)?;
        let pz = standardized(data, z, 1.0)?;
        let x_aug = Mat::<f64>::from_fn(n, 1 + n_z, |i, j| {
            if j == 0 {
                px[(i, 0)]
            } else {
                pz_half[(i, j - 1)]
            }
        });

        let kernel_z = match &self.kernel {
            KernelChoice::All(k) => *k,
            _ => default_rbf(&pz, self.bandwidth, n, n_z),
        };
        let kernel_x = queried_kernel(data, x, &x_aug, self, n_z);
        let kernel_y = queried_kernel(data, y, &py, self, n_z);

        let kx = centered_kernel(kernel_x, &x_aug);
        let ky = centered_kernel(kernel_y, &py);
        let mut kz = centered_kernel(kernel_z, &pz);
        for i in 0..n {
            kz[(i, i)] += self.epsilon;
        }
        let llt = kz
            .llt(Side::Lower)
            .map_err(|e| numeric("Cholesky factorization", e))?;
        let mut rz = llt.inverse();
        for j in 0..n {
            for i in 0..n {
                rz[(i, j)] *= self.epsilon;
            }
        }
        let kxr = &rz * &kx * &rz;
        let kyr = &rz * &ky * &rz;

        let stat = inner(&kxr, &kyr);
        let denom = (inner(&kxr, &kxr) * inner(&kyr, &kyr)).sqrt();
        let effect = if denom > 0.0 { stat / denom } else { 0.0 };

        let vx = scaled_eigenvectors(&kxr)?;
        let vy = scaled_eigenvectors(&kyr)?;
        let gx = &vx * vx.transpose();
        let gy = &vy * vy.transpose();
        let mut tr = 0.0;
        let mut sq = 0.0;
        for j in 0..n {
            for i in 0..n {
                let u = gx[(i, j)] * gy[(i, j)];
                sq += u * u;
                if i == j {
                    tr += u;
                }
            }
        }
        let p_value = gamma_pvalue(stat, tr, 2.0 * sq)?;

        Ok(CiResult {
            statistic: Some(stat),
            p_value,
            dof: None,
            effect_size: Some(effect),
        })
    }

    fn meta(&self) -> TestMeta {
        TestMeta {
            name: "kci",
            data_types: &[DataType::Continuous],
            symmetric: false,
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
    use crate::ci_tests::Hsic;
    use crate::dataset::ColumnKind;
    use crate::rng::SplitMix64;
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

    fn cont(cols: Vec<(&str, Vec<f64>)>) -> Dataset {
        Dataset::from_columns(
            cols.into_iter()
                .map(|(n, v)| (n.to_string(), ColumnKind::Continuous, v))
                .collect(),
        )
        .unwrap()
    }

    /// Columns x, y, z with x = z + 0.5 e1, y = z + 0.5 e2.
    fn chain(n: usize, seed: u64) -> Dataset {
        let mut rng = SplitMix64::new(seed);
        let z = normals(&mut rng, n);
        let e1 = normals(&mut rng, n);
        let e2 = normals(&mut rng, n);
        let x = z.iter().zip(&e1).map(|(a, b)| a + 0.5 * b).collect();
        let y = z.iter().zip(&e2).map(|(a, b)| a + 0.5 * b).collect();
        cont(vec![("x", x), ("y", y), ("z", z)])
    }

    #[test]
    fn empty_z_equals_default_hsic() {
        let d = chain(60, 1);
        let a = Kci::new().test(&d, 0, 1, &[]).unwrap();
        let b = Hsic::new().test(&d, 0, 1, &[]).unwrap();
        assert_eq!(a, b);
    }

    #[test]
    fn heuristic_length_scale_bands() {
        assert_eq!(kci_heuristic_length_scale(199, 1), 1.2);
        assert_eq!(kci_heuristic_length_scale(200, 1), 0.7);
        assert_eq!(kci_heuristic_length_scale(1199, 4), 1.4);
        assert_eq!(kci_heuristic_length_scale(1200, 1), 0.4);
    }

    #[test]
    fn asymmetric_in_x_and_y() {
        let mut rng = SplitMix64::new(3);
        let z = normals(&mut rng, 80);
        let x = normals(&mut rng, 80);
        let e = normals(&mut rng, 80);
        let y = x.iter().zip(&e).map(|(a, b)| a + 0.3 * b).collect();
        let d = cont(vec![("x", x), ("y", y), ("z", z)]);
        let a = Kci::new().test(&d, 0, 1, &[2]).unwrap();
        let b = Kci::new().test(&d, 1, 0, &[2]).unwrap();
        assert!((a.statistic.unwrap() - b.statistic.unwrap()).abs() > 1e-9 * a.statistic.unwrap());
    }

    #[test]
    fn per_column_entry_for_z_is_ignored() {
        let d = chain(60, 5);
        let x = ("x".to_string(), Kernel::Rbf { length_scale: 2.0 });
        let with_z = BTreeMap::from([
            x.clone(),
            ("z".to_string(), Kernel::Rbf { length_scale: 5.0 }),
        ]);
        let without = BTreeMap::from([x]);
        let a = Kci {
            kernel: KernelChoice::PerColumn(with_z),
            ..Kci::new()
        };
        let b = Kci {
            kernel: KernelChoice::PerColumn(without),
            ..Kci::new()
        };
        assert_eq!(
            a.test(&d, 0, 1, &[2]).unwrap(),
            b.test(&d, 0, 1, &[2]).unwrap()
        );
    }

    #[test]
    fn single_kernel_applies_to_z() {
        let d = chain(60, 6);
        let k = Kernel::Rbf { length_scale: 1.0 };
        let all = Kci {
            kernel: KernelChoice::All(k),
            ..Kci::new()
        };
        let map = Kci {
            kernel: KernelChoice::PerColumn(BTreeMap::from([
                ("x".to_string(), k),
                ("y".to_string(), k),
            ])),
            ..Kci::new()
        };
        assert_ne!(
            all.test(&d, 0, 1, &[2]).unwrap().statistic,
            map.test(&d, 0, 1, &[2]).unwrap().statistic
        );
    }

    #[test]
    fn conditional_independence_vs_dependence() {
        let d = chain(200, 11);
        let p = Kci::new().test(&d, 0, 1, &[2]).unwrap().p_value;
        assert!(p > 0.01, "{p}");

        let mut rng = SplitMix64::new(12);
        let z = normals(&mut rng, 200);
        let x = normals(&mut rng, 200);
        let e = normals(&mut rng, 200);
        let y = x.iter().zip(&e).map(|(a, b)| a + 0.3 * b).collect();
        let d = cont(vec![("x", x), ("y", y), ("z", z)]);
        let p = Kci::new().test(&d, 0, 1, &[2]).unwrap().p_value;
        assert!(p < 1e-4, "{p}");
    }

    #[test]
    fn rejects_invalid_epsilon_and_discrete_z() {
        let d = chain(30, 7);
        for eps in [0.0, -1.0, f64::NAN] {
            let t = Kci {
                epsilon: eps,
                ..Kci::new()
            };
            assert!(matches!(t.validate(&d), Err(CiError::InvalidConfig(_))));
            assert!(matches!(
                t.test(&d, 0, 1, &[2]),
                Err(CiError::InvalidConfig(_))
            ));
        }
        let mut rng = SplitMix64::new(8);
        let d = Dataset::from_columns(vec![
            (
                "x".to_string(),
                ColumnKind::Continuous,
                normals(&mut rng, 30),
            ),
            (
                "y".to_string(),
                ColumnKind::Continuous,
                normals(&mut rng, 30),
            ),
            (
                "z".to_string(),
                ColumnKind::Discrete,
                (0..30).map(|i| f64::from(i % 3)).collect(),
            ),
        ])
        .unwrap();
        assert!(matches!(
            Kci::new().test(&d, 0, 1, &[2]),
            Err(CiError::WrongColumnKind { .. })
        ));
    }

    #[test]
    fn perfectly_dependent_is_finite() {
        let mut rng = SplitMix64::new(13);
        let x = normals(&mut rng, 120);
        let z = normals(&mut rng, 120);
        let y = x.clone();
        let d = cont(vec![("x", x), ("y", y), ("z", z)]);
        let r = Kci::new().test(&d, 0, 1, &[2]).unwrap();
        assert!(r.statistic.unwrap().is_finite());
        assert!(r.p_value < 1e-6, "{}", r.p_value);
    }

    #[test]
    fn works_with_unrelated_discrete_columns() {
        let mut rng = SplitMix64::new(9);
        let d = Dataset::from_columns(vec![
            (
                "x".to_string(),
                ColumnKind::Continuous,
                normals(&mut rng, 40),
            ),
            (
                "y".to_string(),
                ColumnKind::Continuous,
                normals(&mut rng, 40),
            ),
            (
                "z".to_string(),
                ColumnKind::Continuous,
                normals(&mut rng, 40),
            ),
            (
                "d".to_string(),
                ColumnKind::Discrete,
                (0..40).map(|i| f64::from(i % 3)).collect(),
            ),
        ])
        .unwrap();
        assert!(Kci::new().test(&d, 0, 1, &[2]).is_ok());
    }
}
