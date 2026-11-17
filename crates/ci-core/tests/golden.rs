//! Fixture-driven acceptance gate.
//!
//! Parses the language-agnostic reference fixture (`tests/fixtures/golden.json`
//! at the repository root) and checks **every** case against the scipy-derived
//! expectations:
//!
//! - The five discrete power-divergence tests (`chi_squared`, `log_likelihood`,
//!   `cressie_read`, `freeman_tukey`, `modified_likelihood`) are run with the
//!   case's own `params.yates`, so both Yates-on and Yates-off rows are covered.
//! - All `pearson_correlation`, `pearson_equivalence`, and `fisher_z` rows.
//! - All `hsic` and `kci` rows, built from the case's kernel/bandwidth/null params.
//! - All `gcm` and `pillai` rows (parameter-free).
//!
//! Every non-null `statistic`/`p_value`/`dof`/`effect_size` field is asserted to
//! within `1e-7` (or, for cases carrying `rel_tol`, within
//! `max(1e-300, rel_tol * |expected|)`), with the `+∞` statistic / `p = 0` degenerate case handled
//! exactly. The test asserts it exercised every supplied fixture case.

use std::collections::BTreeMap;

use fastcit_core::ci_tests::{
    chi_squared::ChiSquared, cressie_read::CressieRead, freeman_tukey::FreemanTukey,
    log_likelihood::LogLikelihood, modified_likelihood::ModifiedLikelihood, FisherZ, Gcm, Hsic,
    Kci, NullDistribution, PearsonCorrelation, PearsonEquivalence, Pillai,
};
use fastcit_core::dataset::{ColumnKind, Dataset};
use fastcit_core::kernel::{Bandwidth, Kernel, KernelChoice};
use fastcit_core::strategy::{CIResult, CITest, DataType};
use serde::Deserialize;

const TOL: f64 = 1e-7;

#[derive(Debug, Default, Deserialize)]
struct Params {
    #[serde(default)]
    delta_threshold: Option<f64>,
    #[serde(default)]
    yates: Option<bool>,
    #[serde(default)]
    kernel: Option<serde_json::Value>,
    #[serde(default)]
    bandwidth: Option<String>,
    #[serde(default)]
    null_dist: Option<String>,
    #[serde(default)]
    n_permutations: Option<usize>,
    #[serde(default)]
    seed: Option<u64>,
    #[serde(default)]
    epsilon: Option<f64>,
}

#[derive(Debug, Deserialize)]
struct ColumnSpec {
    kind: String,
    values: Vec<f64>,
}

#[derive(Debug, Deserialize)]
struct Expected {
    statistic: Option<f64>,
    p_value: Option<f64>,
    dof: Option<usize>,
    effect_size: Option<f64>,
}

#[derive(Debug, Deserialize)]
struct Case {
    id: String,
    test: String,
    #[serde(default)]
    params: Params,
    columns: BTreeMap<String, ColumnSpec>,
    x: String,
    y: String,
    z: Vec<String>,
    expected: Expected,
    #[serde(default)]
    rel_tol: Option<f64>,
}

fn load_cases() -> Vec<Case> {
    let path = concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../tests/fixtures/golden.json"
    );
    let raw = std::fs::read_to_string(path)
        .unwrap_or_else(|e| panic!("failed to read fixture at {path}: {e}"));
    serde_json::from_str(&raw).expect("failed to parse golden.json")
}

/// Build a `Dataset` plus a name->index map from a case's columns, preserving a
/// deterministic ordering so X/Y/Z names resolve correctly.
fn build_dataset(case: &Case) -> (Dataset, BTreeMap<String, usize>) {
    let mut cols = Vec::new();
    let mut index = BTreeMap::new();
    for (i, (name, spec)) in case.columns.iter().enumerate() {
        let kind: DataType = match spec.kind.as_str() {
            "discrete" => ColumnKind::Discrete,
            "continuous" => ColumnKind::Continuous,
            other => panic!("[{}:{}] unknown column kind {other}", case.id, case.test),
        };
        cols.push((name.clone(), kind, spec.values.clone()));
        index.insert(name.clone(), i);
    }
    (
        Dataset::from_columns(cols)
            .unwrap_or_else(|e| panic!("[{}:{}] failed to build dataset: {e}", case.id, case.test)),
        index,
    )
}

/// The `yates` flag for a discrete case (defaults to `true` if unspecified).
fn case_yates(case: &Case) -> bool {
    case.params.yates.unwrap_or(true)
}

fn parse_kernel(v: &serde_json::Value) -> Kernel {
    match v["type"].as_str() {
        Some("rbf") => Kernel::Rbf {
            length_scale: v["length_scale"]
                .as_f64()
                .expect("rbf kernel needs a numeric length_scale"),
        },
        Some("linear") => Kernel::Linear,
        other => panic!("unknown kernel type {other:?}"),
    }
}

/// Maps the fixture's kernel JSON (`null` | kernel | `{"columns": {..}}`).
#[allow(
    clippy::ref_option,
    reason = "mirrors the `Option` field of `Params` directly"
)]
fn kernel_choice(v: &Option<serde_json::Value>) -> KernelChoice {
    match v {
        None | Some(serde_json::Value::Null) => KernelChoice::Auto,
        Some(obj) => match obj.get("columns") {
            Some(columns) => KernelChoice::PerColumn(
                columns
                    .as_object()
                    .expect("columns must be an object")
                    .iter()
                    .map(|(name, k)| (name.clone(), parse_kernel(k)))
                    .collect(),
            ),
            None => KernelChoice::All(parse_kernel(obj)),
        },
    }
}

fn case_bandwidth(case: &Case) -> Bandwidth {
    match case.params.bandwidth.as_deref() {
        Some("heuristic") | None => Bandwidth::Heuristic,
        Some("median") => Bandwidth::Median,
        Some(other) => panic!("[{}:{}] unknown bandwidth {other}", case.id, case.test),
    }
}

fn case_null_dist(case: &Case) -> NullDistribution {
    match case.params.null_dist.as_deref() {
        Some("gamma") | None => NullDistribution::Gamma,
        Some("permutation") => NullDistribution::Permutation {
            n_permutations: case
                .params
                .n_permutations
                .unwrap_or_else(|| panic!("[{}:{}] missing n_permutations", case.id, case.test)),
            seed: case
                .params
                .seed
                .unwrap_or_else(|| panic!("[{}:{}] missing seed", case.id, case.test)),
        },
        Some(other) => panic!("[{}:{}] unknown null_dist {other}", case.id, case.test),
    }
}

fn run_case(case: &Case) -> CIResult {
    let (data, index) = build_dataset(case);
    let x = *index
        .get(&case.x)
        .unwrap_or_else(|| panic!("[{}:{}] unknown x column {}", case.id, case.test, case.x));
    let y = *index
        .get(&case.y)
        .unwrap_or_else(|| panic!("[{}:{}] unknown y column {}", case.id, case.test, case.y));
    let z: Vec<usize> = case
        .z
        .iter()
        .map(|name| {
            *index
                .get(name)
                .unwrap_or_else(|| panic!("[{}:{}] unknown z column {name}", case.id, case.test))
        })
        .collect();

    // Construct each discrete test with the case's own Yates flag so both the
    // Yates-on and Yates-off fixture rows are exercised.
    let test: Box<dyn CITest> = match case.test.as_str() {
        "chi_squared" => Box::new(ChiSquared {
            yates: case_yates(case),
        }),
        "log_likelihood" => Box::new(LogLikelihood {
            yates: case_yates(case),
        }),
        "cressie_read" => Box::new(CressieRead {
            yates: case_yates(case),
        }),
        "freeman_tukey" => Box::new(FreemanTukey {
            yates: case_yates(case),
        }),
        "modified_likelihood" => Box::new(ModifiedLikelihood {
            yates: case_yates(case),
        }),
        "pearson_correlation" => Box::new(PearsonCorrelation::new()),
        "pearson_equivalence" => {
            let delta = case.params.delta_threshold.unwrap_or_else(|| {
                panic!(
                    "[{}:{}] equivalence case missing delta_threshold",
                    case.id, case.test
                )
            });
            Box::new(PearsonEquivalence::new(delta))
        }
        "fisher_z" => Box::new(FisherZ::new()),
        "gcm" => Box::new(Gcm::new()),
        "pillai" => Box::new(Pillai::new()),
        "hsic" => Box::new(Hsic {
            kernel: kernel_choice(&case.params.kernel),
            bandwidth: case_bandwidth(case),
            null_dist: case_null_dist(case),
        }),
        "kci" => Box::new(Kci {
            kernel: kernel_choice(&case.params.kernel),
            bandwidth: case_bandwidth(case),
            epsilon: case
                .params
                .epsilon
                .unwrap_or_else(|| panic!("[{}:{}] kci case missing epsilon", case.id, case.test)),
        }),
        other => panic!(
            "[{}:{}] run_case called for unsupported test {other}",
            case.id, case.test
        ),
    };

    test.test(&data, x, y, &z)
        .unwrap_or_else(|e| panic!("[{}:{}] test execution failed: {e}", case.id, case.test))
}

fn assert_field(name: &str, case: &Case, expected: Option<f64>, actual: Option<f64>) {
    let Some(exp) = expected else {
        assert!(
            actual.is_none(),
            "[{}:{}] expected {name}=None, got {actual:?}",
            case.id,
            case.test,
        );
        return;
    };
    let act = actual.unwrap_or_else(|| {
        panic!(
            "[{}:{}] expected {name}={exp} but result had None",
            case.id, case.test
        )
    });

    // Handle the degenerate `+∞` statistic / `p = 0` case exactly: an infinite
    // expectation requires a matching infinite actual of the same sign (and
    // vice versa). `total_cmp` gives an exact ordering without a float `==`.
    if exp.is_infinite() || act.is_infinite() {
        assert!(
            exp.total_cmp(&act).is_eq(),
            "[{}:{}] {name} mismatch: expected {exp}, got {act} (x={}, y={}, z={:?})",
            case.id,
            case.test,
            case.x,
            case.y,
            case.z,
        );
        return;
    }

    let tolerance = case
        .rel_tol
        .map_or(TOL, |rel| f64::max(1e-300, rel * exp.abs()));
    assert!(
        (act - exp).abs() <= tolerance,
        "[{}:{}] {name} mismatch: expected {exp}, got {act} (x={}, y={}, z={:?})",
        case.id,
        case.test,
        case.x,
        case.y,
        case.z,
    );
}

#[test]
fn golden_fixture_matches() {
    let cases = load_cases();
    let mut counts: BTreeMap<&str, usize> = BTreeMap::new();

    for case in &cases {
        assert!(
            !case.id.is_empty(),
            "[{}:{}] fixture case ID is empty",
            case.id,
            case.test
        );
        let result = run_case(case);

        assert_field("statistic", case, case.expected.statistic, result.statistic);
        assert_field("p_value", case, case.expected.p_value, Some(result.p_value));
        #[allow(clippy::cast_precision_loss)]
        let dof_expected = case.expected.dof.map(|d| d as f64);
        #[allow(clippy::cast_precision_loss)]
        let dof_actual = result.dof.map(|d| d as f64);
        assert_field("dof", case, dof_expected, dof_actual);
        assert_field(
            "effect_size",
            case,
            case.expected.effect_size,
            result.effect_size,
        );

        *counts.entry(case.test.as_str()).or_default() += 1;
    }

    eprintln!("golden fixture: asserted cases per test: {counts:?}");

    // Every test in the fixture must be covered, and every single case asserted.
    let total: usize = counts.values().sum();
    assert_eq!(
        total,
        cases.len(),
        "not every supplied fixture case was asserted: {counts:?}"
    );
    for test in [
        "chi_squared",
        "log_likelihood",
        "cressie_read",
        "freeman_tukey",
        "modified_likelihood",
        "pearson_correlation",
        "pearson_equivalence",
        "fisher_z",
        "hsic",
        "kci",
        "gcm",
        "pillai",
    ] {
        assert!(
            counts.get(test).copied().unwrap_or(0) > 0,
            "no cases asserted for {test}"
        );
    }
}
