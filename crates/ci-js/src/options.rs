//! Constructor options: defaults, accepted keys, and their TypeScript surface.

use std::collections::BTreeMap;

use fastcit_core::ci_tests::{Hsic, Kci, NullDistribution};
use fastcit_core::kernel::{Bandwidth, Kernel, KernelChoice};
use serde::{de::DeserializeOwned, Deserialize};
use wasm_bindgen::prelude::*;

use crate::js_error;

/// Parse optional configuration without silently accepting misspelled keys.
pub(crate) trait Config: DeserializeOwned + Default {
    const ALLOWED_KEYS: &'static [&'static str];

    fn parse(config: Option<js_sys::Object>) -> Result<Self, JsValue> {
        let Some(obj) = config else {
            return Ok(Self::default());
        };
        // serde-wasm-bindgen reads only known fields off a JS object, so
        // unknown keys must be rejected explicitly before deserialization.
        let allowed = Self::ALLOWED_KEYS;
        for key in js_sys::Object::keys(&obj).iter() {
            let key = key.as_string().unwrap_or_default();
            if !allowed.contains(&key.as_str()) {
                return Err(js_error(&format!(
                    "invalid config object: unknown key {key:?} (allowed: {allowed:?})"
                )));
            }
        }
        serde_wasm_bindgen::from_value(obj.into())
            .map_err(|e| js_error(&format!("invalid config object: {e}")))
    }
}

#[wasm_bindgen(typescript_custom_section)]
const TS_DISCRETE_OPTIONS: &'static str = r#"
export interface DiscreteOptions { yates?: boolean; }
"#;

/// Config for the discrete power-divergence tests: `{ yates }` (default `true`).
#[derive(Deserialize)]
#[serde(default, rename_all = "camelCase")]
pub(crate) struct DiscreteConfig {
    pub(crate) yates: bool,
}

impl Default for DiscreteConfig {
    fn default() -> Self {
        // Yates' continuity correction on by default (scipy/pgmpy convention).
        Self { yates: true }
    }
}

impl Config for DiscreteConfig {
    const ALLOWED_KEYS: &'static [&'static str] = &["yates"];
}

/// Config for Pearson correlation and Fisher Z: no options.
#[derive(Deserialize, Default)]
#[serde(default)]
pub(crate) struct EmptyConfig {}

impl Config for EmptyConfig {
    const ALLOWED_KEYS: &'static [&'static str] = &[];
}

#[wasm_bindgen(typescript_custom_section)]
const TS_EQUIVALENCE_OPTIONS: &'static str = r#"
export interface EquivalenceOptions { deltaThreshold?: number; }
"#;

/// Config for Pearson equivalence: `{ deltaThreshold }` (default `0.1`).
#[derive(Deserialize)]
#[serde(default, rename_all = "camelCase")]
pub(crate) struct EquivalenceConfig {
    pub(crate) delta_threshold: f64,
}

impl Default for EquivalenceConfig {
    fn default() -> Self {
        Self {
            delta_threshold: 0.1,
        }
    }
}

impl Config for EquivalenceConfig {
    const ALLOWED_KEYS: &'static [&'static str] = &["deltaThreshold"];
}

#[wasm_bindgen(typescript_custom_section)]
const TS_KERNEL_OPTIONS: &'static str = r#"
export type KernelSpec = { type: "rbf"; lengthScale: number } | { type: "linear" };
export interface HsicOptions {
  kernel?: KernelSpec;
  kernels?: Record<string, KernelSpec>;
  bandwidth?: "heuristic" | "median";
  nullDist?: "gamma" | "permutation";
  nPermutations?: number;
  seed?: number;
}
export interface KciOptions {
  kernel?: KernelSpec;
  kernels?: Record<string, KernelSpec>;
  bandwidth?: "heuristic" | "median";
  epsilon?: number;
}
"#;

/// A kernel as written from JS: `{ type: "rbf", lengthScale }` or `{ type: "linear" }`.
#[derive(Deserialize, Clone, Copy)]
#[serde(tag = "type", rename_all = "lowercase")]
pub(crate) enum KernelSpec {
    #[serde(rename_all = "camelCase")]
    Rbf {
        length_scale: f64,
    },
    Linear,
}

impl From<KernelSpec> for Kernel {
    fn from(spec: KernelSpec) -> Self {
        match spec {
            KernelSpec::Rbf { length_scale } => Kernel::Rbf { length_scale },
            KernelSpec::Linear => Kernel::Linear,
        }
    }
}

#[derive(Deserialize, Clone, Copy, Default)]
#[serde(rename_all = "lowercase")]
enum BandwidthSpec {
    #[default]
    Heuristic,
    Median,
}

impl From<BandwidthSpec> for Bandwidth {
    fn from(spec: BandwidthSpec) -> Self {
        match spec {
            BandwidthSpec::Heuristic => Bandwidth::Heuristic,
            BandwidthSpec::Median => Bandwidth::Median,
        }
    }
}

#[derive(Deserialize, Clone, Copy, Default, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
enum NullDistSpec {
    #[default]
    Gamma,
    Permutation,
}

/// Resolve the mutually exclusive `kernel` / `kernels` options.
fn kernel_choice(
    kernel: Option<KernelSpec>,
    kernels: Option<BTreeMap<String, KernelSpec>>,
) -> Result<KernelChoice, JsValue> {
    match (kernel, kernels) {
        (Some(_), Some(_)) => Err(js_error(
            "invalid config object: `kernel` and `kernels` are mutually exclusive",
        )),
        (Some(k), None) => Ok(KernelChoice::All(k.into())),
        (None, Some(map)) => Ok(KernelChoice::PerColumn(
            map.into_iter().map(|(name, k)| (name, k.into())).collect(),
        )),
        (None, None) => Ok(KernelChoice::Auto),
    }
}

/// Largest integer exactly representable as an f64 (`Number.MAX_SAFE_INTEGER`).
const MAX_SAFE_INTEGER: f64 = 9_007_199_254_740_991.0;

/// Check `value` is an integer in `[min, MAX_SAFE_INTEGER]`.
fn safe_integer(name: &str, value: f64, min: f64) -> Result<f64, JsValue> {
    if value.is_finite() && value.fract() == 0.0 && (min..=MAX_SAFE_INTEGER).contains(&value) {
        Ok(value)
    } else {
        Err(js_error(&format!(
            "invalid config object: {name} must be a safe integer >= {min}, got {value}"
        )))
    }
}

/// Config for HSIC (all optional; pgmpy defaults).
#[derive(Deserialize, Default)]
#[serde(default, rename_all = "camelCase")]
pub(crate) struct HsicConfig {
    kernel: Option<KernelSpec>,
    kernels: Option<BTreeMap<String, KernelSpec>>,
    bandwidth: BandwidthSpec,
    null_dist: NullDistSpec,
    n_permutations: Option<f64>,
    seed: Option<f64>,
}

impl Config for HsicConfig {
    const ALLOWED_KEYS: &'static [&'static str] = &[
        "kernel",
        "kernels",
        "bandwidth",
        "nullDist",
        "nPermutations",
        "seed",
    ];
}

impl HsicConfig {
    /// Validate the options and build the core test.
    #[allow(
        clippy::cast_possible_truncation,
        clippy::cast_sign_loss,
        reason = "both values were just checked to be safe non-negative integers"
    )]
    pub(crate) fn build(self) -> Result<Hsic, JsValue> {
        let n_permutations =
            safe_integer("nPermutations", self.n_permutations.unwrap_or(100.0), 1.0)?;
        let seed = safe_integer("seed", self.seed.unwrap_or(0.0), 0.0)?;
        let null_dist = match self.null_dist {
            NullDistSpec::Gamma => NullDistribution::Gamma,
            NullDistSpec::Permutation => NullDistribution::Permutation {
                n_permutations: n_permutations as usize,
                seed: seed as u64,
            },
        };
        Ok(Hsic {
            kernel: kernel_choice(self.kernel, self.kernels)?,
            bandwidth: self.bandwidth.into(),
            null_dist,
        })
    }
}

/// Config for KCI (all optional; pgmpy defaults).
#[derive(Deserialize)]
#[serde(default, rename_all = "camelCase")]
pub(crate) struct KciConfig {
    kernel: Option<KernelSpec>,
    kernels: Option<BTreeMap<String, KernelSpec>>,
    bandwidth: BandwidthSpec,
    epsilon: f64,
}

impl Default for KciConfig {
    fn default() -> Self {
        Self {
            kernel: None,
            kernels: None,
            bandwidth: BandwidthSpec::default(),
            epsilon: Kci::new().epsilon,
        }
    }
}

impl Config for KciConfig {
    const ALLOWED_KEYS: &'static [&'static str] = &["kernel", "kernels", "bandwidth", "epsilon"];
}

impl KciConfig {
    /// Validate the options and build the core test.
    pub(crate) fn build(self) -> Result<Kci, JsValue> {
        Ok(Kci {
            kernel: kernel_choice(self.kernel, self.kernels)?,
            bandwidth: self.bandwidth.into(),
            epsilon: self.epsilon,
        })
    }
}
