//! Conversion helpers from core types to R objects and errors.

use std::collections::BTreeMap;

use ci_core::error::CiError as CoreError;
use ci_core::kernel::{Bandwidth, Kernel, KernelChoice};
use ci_core::strategy::CiResult as CoreResult;
use extendr_api::prelude::*;
use extendr_api::Result;

/// Map a core [`CoreError`] onto an extendr [`Error`], which extendr raises as
/// an R error at the call site.
pub fn to_r_error(err: CoreError) -> Error {
    Error::Other(err.to_string())
}

/// Convert a core [`CoreResult`] into the uniform named R list
/// `list(statistic, p_value, dof, effect_size)`.
///
/// Absent optional fields (`statistic`, `dof`, `effect_size`) become R `NULL`;
/// `p_value` is always present. `dof` is returned as an integer.
#[allow(
    clippy::cast_possible_truncation,
    clippy::cast_possible_wrap,
    reason = "dof is a small degrees-of-freedom count, far below i32::MAX"
)]
pub fn result_to_list(result: &CoreResult) -> Robj {
    list!(
        statistic = opt_or_null(result.statistic),
        p_value = result.p_value,
        dof = opt_or_null(result.dof.map(|d| d as i32)),
        effect_size = opt_or_null(result.effect_size),
    )
    .into()
}

/// Wrap `Some(v)` as its R scalar and `None` as R `NULL` (not `NA`).
fn opt_or_null<T: Into<Robj>>(v: Option<T>) -> Robj {
    v.map_or_else(|| r!(NULL), Into::into)
}

/// Largest integer R doubles represent exactly (2^53).
pub const MAX_SAFE: f64 = 9_007_199_254_740_992.0;

/// Validate that `value` is a finite whole number in `[min, max]`.
///
/// Never truncates: NA, NaN, infinities, fractions, and out-of-range values
/// are errors.
pub fn whole_number(value: f64, name: &str, min: f64, max: f64) -> Result<f64> {
    if !value.is_finite() || value.fract() != 0.0 || value < min || value > max {
        return Err(Error::Other(format!(
            "{name} must be a whole number between {min} and {max}, got {value}"
        )));
    }
    Ok(value)
}

/// Parse a bandwidth-rule string.
pub fn parse_bandwidth(name: &str) -> Result<Bandwidth> {
    match name {
        "heuristic" => Ok(Bandwidth::Heuristic),
        "median" => Ok(Bandwidth::Median),
        other => Err(Error::Other(format!(
            "bandwidth must be \"heuristic\" or \"median\", got {other:?}"
        ))),
    }
}

/// Build a core [`Kernel`] from its flattened type string and length scale
/// (`NA` for linear).
fn parse_kernel(kind: &str, length_scale: f64) -> Result<Kernel> {
    match kind {
        "rbf" => Ok(Kernel::Rbf { length_scale }),
        "linear" => Ok(Kernel::Linear),
        other => Err(Error::Other(format!(
            "kernel type must be \"rbf\" or \"linear\", got {other:?}"
        ))),
    }
}

/// Rebuild a [`KernelChoice`] from the flattened R representation: a mode
/// (`"auto"`, `"all"`, `"per_column"`) plus parallel name/type/length-scale
/// vectors (a single entry for `"all"`).
pub fn parse_kernel_choice(
    mode: &str,
    names: &Strings,
    types: &Strings,
    length_scales: &Doubles,
) -> Result<KernelChoice> {
    let n = types.len();
    if length_scales.len() != n || (mode == "per_column" && names.len() != n) {
        return Err(Error::Other(
            "kernel names, types and length scales must have the same length".to_string(),
        ));
    }
    let entry = |i: usize| parse_kernel(types.elt(i).as_ref(), length_scales.elt(i).0);
    match mode {
        "auto" => Ok(KernelChoice::Auto),
        "all" => {
            if n != 1 {
                return Err(Error::Other(
                    "kernel mode \"all\" needs one kernel".to_string(),
                ));
            }
            Ok(KernelChoice::All(entry(0)?))
        }
        "per_column" => {
            let mut map = BTreeMap::new();
            for i in 0..n {
                let name = names.elt(i).to_string();
                if map.insert(name.clone(), entry(i)?).is_some() {
                    return Err(Error::Other(format!("duplicate kernel column: {name:?}")));
                }
            }
            Ok(KernelChoice::PerColumn(map))
        }
        other => Err(Error::Other(format!("unknown kernel mode: {other:?}"))),
    }
}
