//! Concrete conditional-independence tests.
//!
//! Five discrete power-divergence tests ([`ChiSquared`], [`LogLikelihood`],
//! [`CressieRead`], [`FreemanTukey`], [`ModifiedLikelihood`]) share the
//! λ-parameterized [`crate::discrete`] engine; three continuous
//! tests ([`PearsonCorrelation`], [`FisherZ`], [`PearsonEquivalence`]) cover the
//! partial-correlation path. Two continuous kernel tests, [`Hsic`] (unconditional) and
//! [`Kci`] (conditional), compare dense kernel matrices.
//! [`Gcm`] is the continuous generalized covariance measure (linear residuals);
//! [`Pillai`] is Pillai's trace on linear residuals and handles mixed
//! discrete/continuous data.

mod power_divergence;

/// Pearson chi-squared conditional-independence test (power divergence, λ = 1).
pub mod chi_squared {
    pub use super::power_divergence::ChiSquared;
}
/// Cressie-Read conditional-independence test (power divergence, λ = 2/3).
pub mod cressie_read {
    pub use super::power_divergence::CressieRead;
}
pub mod fisher_z;
pub mod gcm;
pub mod hsic;
pub mod kci;
/// Freeman-Tukey conditional-independence test (power divergence, λ = −1/2).
pub mod freeman_tukey {
    pub use super::power_divergence::FreemanTukey;
}
/// Log-likelihood (G-test) conditional-independence test (power divergence, λ = 0).
pub mod log_likelihood {
    pub use super::power_divergence::LogLikelihood;
}
/// Modified log-likelihood (Neyman) conditional-independence test
/// (power divergence, λ = −1).
pub mod modified_likelihood {
    pub use super::power_divergence::ModifiedLikelihood;
}
pub mod pearson_correlation;
pub mod pearson_equivalence;
pub mod pillai;

pub use chi_squared::ChiSquared;
pub use cressie_read::CressieRead;
pub use fisher_z::FisherZ;
pub use freeman_tukey::FreemanTukey;
pub use gcm::Gcm;
pub use hsic::{Hsic, NullDistribution};
pub use kci::Kci;
pub use log_likelihood::LogLikelihood;
pub use modified_likelihood::ModifiedLikelihood;
pub use pearson_correlation::PearsonCorrelation;
pub use pearson_equivalence::PearsonEquivalence;
pub use pillai::Pillai;
