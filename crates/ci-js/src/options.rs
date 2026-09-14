//! Constructor options: defaults, accepted keys, and their TypeScript surface.

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
