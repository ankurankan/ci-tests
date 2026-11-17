---
myst:
  html_meta:
    description: FastCIT is a Rust library of conditional independence tests for causal discovery, with bindings for Python, R and JavaScript.
---

# FastCIT: Fast Conditional Independence Tests

::::::{grid} 1 1 2 2
:gutter: 3
:class-container: hero-grid

:::::{grid-item}
:class: hero-logo-panel

```{image} _static/images/logo.png
:alt: pgmpy logo
:width: 220px
:align: center
```

:::::

:::::{grid-item}
:class: hero-copy-panel

::::{container} hero-subtitle
Conditional independence tests for causal discovery
::::

FastCIT is a library of conditional independence tests for causal discovery.
It has a Rust core and bindings for Python, R and JavaScript.
All tests share one API in each language.
FastCIT is part of the [pgmpy](https://pgmpy.org/) project.

::::{container} hero-actions

```{button-link} #quickstart
:color: primary
:outline:

Quickstart
```

```{button-ref} tests/index
:ref-type: doc
:color: primary
:outline:

Available tests
```

```{button-link} #runtime-comparison
:color: primary
:outline:

Runtime Comparison
```

```{button-ref} api
:ref-type: doc
:color: primary
:outline:

API reference
```

::::
:::::
::::::

## Install

::::{tab-set}
:sync-group: language

:::{tab-item} Python
:sync: python

```bash
pip install fastcit
```

:::

:::{tab-item} R
:sync: r

```r
install.packages("fastcit")
```

:::

:::{tab-item} JavaScript
:sync: javascript

```bash
npm install fastcit
```

:::

:::{tab-item} Rust
:sync: rust

```bash
cargo add fastcit-core
```

:::
::::

## Quickstart

::::{tab-set}
:sync-group: language

:::{tab-item} Python
:sync: python

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

:::

:::{tab-item} R
:sync: r

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

:::

:::{tab-item} JavaScript
:sync: javascript

```javascript
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

:::

:::{tab-item} Rust
:sync: rust

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

:::
::::

## One API for all tests

Every test has the same calls and the same result fields.
To change the test, change only the constructor.
HSIC takes no Z.

::::{tab-set}
:sync-group: language

:::{tab-item} Python
:sync: python

```python
test = fastcit.FisherZ(data)  # or fastcit.KCI(data), fastcit.GCM(data), ...

result = test.run_test("X", "Y", ["Z"])
# result has statistic, p_value, dof and effect_size

test.is_independent("X", "Y", ["Z"], significance_level=0.05)
```

:::

:::{tab-item} R
:sync: r

```r
test <- fisher_z(data)  # or kci(data), gcm(data), ...

res <- run_test(test, "X", "Y", "Z")
# res has statistic, p_value, dof and effect_size

is_independent(test, "X", "Y", "Z", significance_level = 0.05)
```

:::

:::{tab-item} JavaScript
:sync: javascript

```javascript
const test = new FisherZ(data); // or new KCI(data), new GCM(data), ...

const result = test.runTest("X", "Y", ["Z"]);
// result has statistic, pValue, dof and effectSize

test.isIndependent("X", "Y", ["Z"], 0.05);
```

:::

:::{tab-item} Rust
:sync: rust

```rust
let test = FisherZ::new(); // or Kci::new(), Gcm::new(), ...

let result = test.test(&data, x, y, &[z])?;
// result has statistic, p_value, dof and effect_size

let independent = test.is_independent(&data, x, y, &[z], 0.05)?;
```

:::
::::

## Runtime Comparison

::::{tab-set}
:sync-group: language

:::{tab-item} Python
:sync: python

```{include} ../benchmarks/results/summary.md
:start-after: "## Python packages, median time of one call"
:end-before: "## R packages, median time of one call"
```

:::

:::{tab-item} R
:sync: r

```{include} ../benchmarks/results/summary.md
:start-after: "## R packages, median time of one call"
:end-before: "## Python packages, total time of one pass"
```

:::
::::

## Available tests

```{include} _includes/test-table.md
```

## API reference

Each language has its own API reference.

```{include} _includes/api-cards.md
```

```{toctree}
:hidden:

Conditional Independence Tests <tests/index>
Benchmark <benchmark>
API reference <api>
```
