# FastCIT: Fast Conditional Independence Tests

[![CI](https://img.shields.io/github/actions/workflow/status/pgmpy/ci-tests/rust.yml?branch=main&logo=github&label=CI)](https://github.com/pgmpy/ci-tests/actions)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/pgmpy/ci-tests/blob/main/LICENSE)

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

Open the block for your language. Each example builds a dataset, runs one test, and prints the p-value.

<details>
<summary>Python</summary>

```python
import numpy as np
import pandas as pd
import fastcit

rng = np.random.default_rng(0)
z = rng.standard_normal(500)
df = pd.DataFrame({
    "X": z + rng.standard_normal(500),
    "Y": z + rng.standard_normal(500),
    "Z": z,
})

data = fastcit.Dataset.from_pandas(df)
test = fastcit.FisherZ(data)
result = test.run_test("X", "Y", ["Z"])
print(result.p_value)
```

</details>

<details>
<summary>R</summary>

```r
library(fastcit)

set.seed(0)
z <- rnorm(500)
df <- data.frame(X = z + rnorm(500), Y = z + rnorm(500), Z = z)

data <- dataset(df)
test <- fisher_z(data)
res <- run_test(test, "X", "Y", "Z")
print(res$p_value)
```

</details>

<details>
<summary>JavaScript</summary>

```js
const { Dataset, FisherZ } = require("fastcit");

const n = 500;
const z = Array.from({ length: n }, () => Math.random());
const x = z.map((v) => v + Math.random());
const y = z.map((v) => v + Math.random());

const data = new Dataset({
  X: { kind: "continuous", values: x },
  Y: { kind: "continuous", values: y },
  Z: { kind: "continuous", values: z },
});
const test = new FisherZ(data);
const result = test.runTest("X", "Y", ["Z"]);
console.log(result.pValue);
```

</details>

<details>
<summary>Rust</summary>

```rust
use fastcit_core::ci_tests::FisherZ;
use fastcit_core::dataset::{ColumnKind, Dataset};
use fastcit_core::strategy::CITest;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let z: Vec<f64> = (0..500).map(|i| ((i * 37 % 101) as f64) / 10.0).collect();
    let x: Vec<f64> = z.iter().enumerate().map(|(i, v)| v + ((i * 53 % 97) as f64) / 10.0).collect();
    let y: Vec<f64> = z.iter().enumerate().map(|(i, v)| v + ((i * 29 % 89) as f64) / 10.0).collect();

    let data = Dataset::from_columns(vec![
        ("X".into(), ColumnKind::Continuous, x),
        ("Y".into(), ColumnKind::Continuous, y),
        ("Z".into(), ColumnKind::Continuous, z),
    ])?;
    let (x, y, z) = (
        data.index_of("X").unwrap(),
        data.index_of("Y").unwrap(),
        data.index_of("Z").unwrap(),
    );
    let result = FisherZ::new().test(&data, x, y, &[z])?;
    println!("{}", result.p_value);
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
A dash means the package does not offer the test, or the benchmark has no result.

The Python run and the R run used the same machine. It has an Intel Core Ultra 5 125U (14 logical CPUs) and runs Linux. Both runs took place on 2026-11-16. The pgmpy version is `dev`, commit a67c17d9.
FastCIT runs on one thread. On this machine, the Python packages use numpy with 14 OpenBLAS threads.
FastCIT is slower than andrey-core on KCI at n = 300 and n = 1 000. It is also slower than pgmpy on KCI at n = 1 000.

### Python packages, median time of one call

| Test | FastCIT | pgmpy dev | causal-learn | andrey-core |
|---|---:|---:|---:|---:|
| χ² | 0.124 | 0.238ᶜ | 0.328 | 0.283ᵇ |
| G² | 0.118 | 0.162ᶜ* | 0.173 | 0.259ᵇ |
| Fisher-zᵉ | 0.001 | 1.01 | 0.044 | 0.013 |
| Pearson tᵉ | 0.001 | 0.965 | — | 0.013 |
| HSIC (n = 300) | 0.902 | 1.68 | 1.81ᵈ | 1.49ᵈ |
| KCI (n = 300) | 18.2 | 37.8 | 54.2 | 13.0 |
| KCI (n = 1 000) | 482 | 383 | 900 | 392 |
| GCM | 0.592 | 4.02 | — | — |
| Pillai | 0.124 | 142ᵃ | — | — |

- ᵃ pgmpy runs a random-forest Pillai test. FastCIT runs a linear Pillai test. The two tests differ.
- ᵇ andrey-core χ² and G² use a different degrees-of-freedom rule from FastCIT.
- ᶜ pgmpy applies the Yates correction and cannot turn it off. FastCIT runs without it.
- ᵈ Different null approximation or kernel width rule from FastCIT.
- ᵉ The time does not include the one-time setup. FastCIT, causal-learn and andrey-core precompute the correlation matrix. FastCIT computes it in the first call and keeps it. pgmpy computes it in every call. With the setup included, andrey-core finishes a pass faster than FastCIT on Fisher-z and Pearson t. See the totals in [summary.md](benchmarks/results/summary.md).
- \* pgmpy returned NaN for one G² query. The median leaves it out.

### R packages, median time of one call

| Test | FastCIT (R) | pcalg | bnlearn | dHSIC |
|---|---:|---:|---:|---:|
| χ² | 0.212 | — | 0.635ᶠᵍ | — |
| G² | 0.093 | 11.6ᶠ | 0.315ᶠᵍ | — |
| Fisher-zᵉ | 0.015 | 0.033 | 0.398ᵍ | — |
| Pearson tᵉ | 0.013 | — | 0.394ᵍ | — |
| HSIC (median width) | 1.40 | — | — | 6.10ᵈ |

- ᵈ Different null approximation or kernel width rule from FastCIT.
- ᵉ The time does not include the one-time setup. FastCIT and pcalg precompute the correlation matrix. FastCIT computes it in the first call and keeps it. bnlearn computes it in every call. See the totals in [summary.md](benchmarks/results/summary.md).
- ᶠ Uses the nominal degrees of freedom. FastCIT uses the adjusted degrees of freedom.
- ᵍ bnlearn ci.test() checks the whole data frame in each call. The benchmark gives it only the columns of the query.

The [benchmarks](benchmarks/) folder explains the method and the total time of one pass. It also shows how to run the benchmark.

## Documentation and contributing

Read the [API documentation](https://pgmpy.github.io/ci-tests/).
Read [CONTRIBUTING.md](CONTRIBUTING.md) before you open a pull request.

## License

FastCIT uses the [MIT License](LICENSE).
