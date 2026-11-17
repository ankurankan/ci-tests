use std::f64::consts::PI;

use fastcit_core::ci_tests::PearsonEquivalence;
use fastcit_core::dataset::{ColumnKind, Dataset};
use fastcit_core::strategy::CITest;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Each language makes its own random data, so the values differ from the other tabs.
    // Seeded generator (Park-Miller), so every run gives the same data.
    let mut seed = 12345.0_f64;
    let mut uniform = move || {
        seed = seed * 16807.0 % 2_147_483_647.0;
        seed / 2_147_483_647.0
    };
    let mut normal = || (-2.0 * uniform().ln()).sqrt() * (2.0 * PI * uniform()).cos();
    let z: Vec<f64> = (0..2000).map(|_| normal()).collect();
    let x: Vec<f64> = z.iter().map(|v| v + normal()).collect(); // X and Y depend on Z only
    let y: Vec<f64> = z.iter().map(|v| v + normal()).collect();

    let data = Dataset::from_columns(vec![
        ("X".into(), ColumnKind::Continuous, x),
        ("Y".into(), ColumnKind::Continuous, y),
        ("Z".into(), ColumnKind::Continuous, z),
    ])?;
    let x = data.index_of("X").unwrap();
    let y = data.index_of("Y").unwrap();
    let z = data.index_of("Z").unwrap();
    // A small p-value supports equivalence: |rho| < threshold, so X and Y are independent given Z.
    let result = PearsonEquivalence::new(0.1).test(&data, x, y, &[z])?;
    println!("{:?}", result.statistic);
    // Some(-0.01296)
    println!("{:?}", result.p_value);
    // 4.734e-5
    println!("{:?}", result.dof);
    // None
    println!("{:?}", result.effect_size);
    // Some(0.01296)
    Ok(())
}
