use fastcit_core::ci_tests::LogLikelihood;
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
    let n = 500;
    let z: Vec<f64> = (0..n).map(|_| (uniform() * 3.0).floor()).collect();
    // X and Y each copy Z about 40% of the time, so they depend on Z only.
    let mut copy = |v: f64| {
        if uniform() < 0.4 {
            v
        } else {
            (uniform() * 3.0).floor()
        }
    };
    let x: Vec<f64> = z.iter().map(|&v| copy(v)).collect();
    let y: Vec<f64> = z.iter().map(|&v| copy(v)).collect();

    let data = Dataset::from_columns(vec![
        ("X".into(), ColumnKind::Discrete, x),
        ("Y".into(), ColumnKind::Discrete, y),
        ("Z".into(), ColumnKind::Discrete, z),
    ])?;
    let x = data.index_of("X").unwrap();
    let y = data.index_of("Y").unwrap();
    let z = data.index_of("Z").unwrap();
    let result = LogLikelihood::new().test(&data, x, y, &[z])?;
    println!("{:?}", result.statistic);
    // Some(14.53)
    println!("{:?}", result.p_value);
    // 0.2684
    println!("{:?}", result.dof);
    // Some(12)
    println!("{:?}", result.effect_size);
    // Some(0.1205)
    Ok(())
}
