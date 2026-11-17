use std::f64::consts::PI;

use fastcit_core::ci_tests::Hsic;
use fastcit_core::dataset::{ColumnKind, Dataset};
use fastcit_core::kernel::Bandwidth;
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
    let x: Vec<f64> = (0..300).map(|_| normal()).collect();
    // Nonlinear dependence with zero correlation.
    let y: Vec<f64> = x.iter().map(|v| v * v + 0.5 * normal()).collect();

    let data = Dataset::from_columns(vec![
        ("X".into(), ColumnKind::Continuous, x),
        ("Y".into(), ColumnKind::Continuous, y),
    ])?;
    let x = data.index_of("X").unwrap();
    let y = data.index_of("Y").unwrap();
    let result = Hsic {
        bandwidth: Bandwidth::Median,
        ..Hsic::new()
    }
    .test(&data, x, y, &[])?;
    println!("{:?}", result.statistic);
    // Some(2488.9)
    println!("{:?}", result.p_value);
    // 1.902e-38
    println!("{:?}", result.dof);
    // None
    println!("{:?}", result.effect_size);
    // Some(0.3257)
    Ok(())
}
