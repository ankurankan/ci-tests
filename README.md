# FastCIT: Fast Conditional Independence Tests

[![CI](https://img.shields.io/github/actions/workflow/status/pgmpy/FastCIT/rust.yml?branch=main&logo=github&label=CI)](https://github.com/pgmpy/FastCIT/actions)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/pgmpy/FastCIT/blob/main/LICENSE)

FastCIT is a library of conditional independence tests for causal discovery. FastCIT has a Rust core. Bindings exist for Python, R and JavaScript.

## Install

Choose your language. Run one command.

| Language | Command |
|---|---|
| Python | `pip install fastcit` |
| JavaScript | `npm install fastcit` |
| R | `install.packages("fastcit")` |
| Rust | `cargo add fastcit-core` |

## Quick start

Open the block for your language. Each example builds a dataset, runs one test, and prints the result fields with their values.
Each language makes its own random data, so the values differ between the language tabs.
With the same data, all languages give the same result.

<details>
<summary>Python</summary>

```pycon
>>> import numpy as np
>>> import fastcit

>>> # Each language makes its own random data, so the values differ from the other tabs.
>>> rng = np.random.default_rng(0)
>>> n = 500
>>> z = rng.standard_normal(n)
>>> x = z + rng.standard_normal(n)  # X and Y depend on Z only
>>> y = z + rng.standard_normal(n)
>>> data = fastcit.Dataset({
...     "X": ("continuous", x),
...     "Y": ("continuous", y),
...     "Z": ("continuous", z),
... })

>>> test = fastcit.FisherZ(data)
>>> result = test.run_test("X", "Y", ["Z"])
>>> result.statistic
-0.5566
>>> result.p_value
0.5778
>>> print(result.dof)
None
>>> result.effect_size
0.02499
```

</details>

<details>
<summary>R</summary>

```r
library(fastcit)

# Each language makes its own random data, so the values differ from the other tabs.
set.seed(0)
n <- 500
z <- rnorm(n)
x <- z + rnorm(n) # X and Y depend on Z only
y <- z + rnorm(n)
df <- data.frame(X = x, Y = y, Z = z)

data <- dataset(df)
test <- fisher_z(data)
res <- run_test(test, "X", "Y", "Z")
print(res$statistic)
#> [1] -0.1752
print(res$p_value)
#> [1] 0.8609
print(res$dof)
#> NULL
print(res$effect_size)
#> [1] 0.007868
```

</details>

<details>
<summary>JavaScript</summary>

```js
const { Dataset, FisherZ } = require("fastcit");

// Each language makes its own random data, so the values differ from the other tabs.
// Seeded generator (Park-Miller), so every run gives the same data.
let seed = 12345;
const uniform = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
const normal = () =>
  Math.sqrt(-2 * Math.log(uniform())) * Math.cos(2 * Math.PI * uniform());
const draw = (n, f) => Array.from({ length: n }, f);

const n = 500;
const z = draw(n, normal);
const x = z.map((v) => v + normal()); // X and Y depend on Z only
const y = z.map((v) => v + normal());

const data = new Dataset({
  X: { kind: "continuous", values: x },
  Y: { kind: "continuous", values: y },
  Z: { kind: "continuous", values: z },
});

const test = new FisherZ(data);
const result = test.runTest("X", "Y", ["Z"]);
console.log(result.statistic);
// -0.9402
console.log(result.pValue);
// 0.3471
console.log(result.dof);
// null
console.log(result.effectSize);
// 0.04219
```

</details>

<details>
<summary>Rust</summary>

```rust
use std::f64::consts::PI;

use fastcit_core::ci_tests::FisherZ;
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
    let z: Vec<f64> = (0..500).map(|_| normal()).collect();
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
    let result = FisherZ::new().test(&data, x, y, &[z])?;
    println!("{:?}", result.statistic);
    // Some(-0.9402)
    println!("{:?}", result.p_value);
    // 0.3471
    println!("{:?}", result.dof);
    // None
    println!("{:?}", result.effect_size);
    // Some(0.04219)
    Ok(())
}
```

</details>

## Available tests

| Test | Data type |
|---|---|
| Chi-squared (`chi_squared`) | Discrete |
| Log-likelihood (`log_likelihood`) | Discrete |
| Cressie-Read (`cressie_read`) | Discrete |
| Freeman-Tukey (`freeman_tukey`) | Discrete |
| Modified log-likelihood (`modified_likelihood`) | Discrete |
| Pearson correlation (`pearson_correlation`) | Continuous |
| Fisher-z (`fisher_z`) | Continuous |
| Pearson equivalence (`pearson_equivalence`) | Continuous |
| HSIC (`hsic`) | Continuous |
| KCI (`kci`) | Continuous |
| GCM (`gcm`) | Continuous |
| Pillai's trace (`pillai`) | Mixed (discrete and continuous) |

Python and JavaScript use class names, for example `FisherZ` and `PillaiTrace`.

## Performance

The tables show the median time of one test call, in milliseconds. Lower is better.
A dash means the package has no test with this definition, or the benchmark has no result.

The Python runs and the R runs used the same machine. It has an Intel Core Ultra 5 125U (14 logical CPUs) and runs Linux. All runs took place on 2026-11-16, on AC power with the `performance` power profile. The pgmpy version is `dev`, commit a67c17d9.
Each language ran three times, each time in a new process. Each cell is the median of the three run values.
FastCIT runs on one thread. The Python runs used 12 of the 14 logical CPUs, and numpy used 12 OpenBLAS threads.
The dowhy column comes from a second interpreter, Python 3.11, because dowhy does not support Python 3.14.
In Python, pgmpy is faster than FastCIT on KCI at n = 300 and at n = 1 000. On KCI at n = 1 000, causal-learn is also faster.
In R, Rfast is faster than FastCIT on χ² and G². In every other row of both tables, FastCIT has the lowest time.

### Python packages, median time of one call

| Test | FastCIT | pgmpy dev | causal-learn | gcastle | tigramite | pingouin | hyppo | dowhy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| χ² | 0.049 | 0.098ᵇ | 0.128 | 8.47ᵇ | — | — | — | — |
| G² | 0.048 | 0.094ᵇ* | 0.131 | 8.46ᵇ | 1.78 | — | — | — |
| Cressie-Read | 0.050 | 0.098ᵇ | — | 8.63ᵇ | — | — | — | — |
| Freeman-Tukey | 0.050 | 0.094ᵇ* | — | 3.68ᵇ* | — | — | — | — |
| Modified log-likelihood | 0.048 | 0.091ᵇ* | — | 8.67ᵇ | — | — | — | — |
| Fisher-zᵈ | 0.001 | 0.945 | 0.043 | 0.143 | — | — | — | — |
| Pearson tᵈ | 0.001 | 0.880 | — | — | 1.65 | 3.59 | — | — |
| HSIC (n = 300) | 1.21 | 1.66 | 1.67ᶜ | — | — | — | 3.67ᶜ | — |
| KCI (n = 300) | 17.3 | 16.3 | 27.8ᶜ | — | — | — | — | — |
| KCI (n = 1 000) | 503 | 258 | 449 | — | — | — | — | — |
| GCM | 0.404 | 4.03 | — | — | — | — | — | 1.65 |
| Pillai | 0.143 | 141ᵃ | — | — | — | — | — | — |

- ᵃ pgmpy runs a random-forest Pillai test. FastCIT runs a linear Pillai test. The two tests differ.
- ᵇ pgmpy and gcastle apply the Yates correction on 2 × 2 tables and cannot turn it off. FastCIT runs without it.
- ᶜ Different null approximation or kernel width rule from FastCIT.
- ᵈ The time does not include the one-time setup. FastCIT and causal-learn precompute the correlation matrix. FastCIT computes it in the first call and keeps it. The other packages in these rows compute it in every call. See the totals in [summary.md](benchmarks/results/summary.md).
- \* pgmpy returned NaN for 1 G² query, 15 Freeman-Tukey queries and 1 modified log-likelihood query. gcastle returned NaN for 15 Freeman-Tukey queries. The median uses only the queries with a result. Those queries can cost less or more than the excluded ones. Compare such a cell with care.

### R packages, median time of one call

| Test | FastCIT (R) | pcalg | bnlearn | dHSIC | Rfast | ppcor | comets |
|---|---:|---:|---:|---:|---:|---:|---:|
| χ² | 0.067 | — | 0.302ᵉᶠ | — | 0.034ᵉ* | — | — |
| G² | 0.066 | 5.27ᵉ | 0.301ᵉᶠ | — | 0.041ᵉ | — | — |
| Fisher-zᵈ | 0.013 | 0.032 | 0.378ᶠ | — | — | — | — |
| Pearson tᵈ | 0.013 | — | 0.380ᶠ | — | — | 0.782ᵍ | — |
| HSIC (median width) | 1.41 | — | — | 5.79ᶜ | — | — | — |
| GCM | 0.479 | — | — | — | — | — | 20.8 |

- ᶜ Different null approximation or kernel width rule from FastCIT.
- ᵈ The time does not include the one-time setup. FastCIT and pcalg precompute the correlation matrix. FastCIT computes it in the first call and keeps it. bnlearn and ppcor compute it in every call. See the totals in [summary.md](benchmarks/results/summary.md).
- ᵉ Uses the nominal degrees of freedom. FastCIT uses the adjusted degrees of freedom.
- ᶠ bnlearn ci.test() checks the whole data frame in each call. The benchmark gives it only the columns of the query.
- ᵍ ppcor needs at least one conditioning variable. For a query with an empty set, the benchmark calls stats::cor.test, which runs the same t-test.
- \* Rfast returned NaN for 6 χ² queries. The median uses only the queries with a result. Those queries can cost less or more than the excluded ones. Compare such a cell with care.

The [benchmarks](benchmarks/) folder explains the method and the total time of one pass. It also shows how to run the benchmark.
[summary.md](benchmarks/results/summary.md) gives the smallest and the largest run value of each cell.

## Documentation and contributing

Read the [API documentation](https://pgmpy.org/FastCIT/).
Read [CONTRIBUTING.md](CONTRIBUTING.md) before you open a pull request.

## License

FastCIT uses the [MIT License](LICENSE).
