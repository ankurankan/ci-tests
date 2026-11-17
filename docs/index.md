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

```{literalinclude} ../crates/ci-python/examples/fisher_z.pycon
:language: pycon
```

:::

:::{tab-item} R
:sync: r

```{literalinclude} ../crates/ci-r/inst/examples/tests/fisher_z.R
:language: r
```

:::

:::{tab-item} JavaScript
:sync: javascript

```{literalinclude} ../crates/ci-js/examples/fisher_z.js
:language: javascript
```

:::

:::{tab-item} Rust
:sync: rust

```{literalinclude} ../crates/ci-core/examples/fisher_z.rs
:language: rust
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
# result.statistic, result.p_value, result.dof, result.effect_size

test.is_independent("X", "Y", ["Z"], significance_level=0.05)
```

:::

:::{tab-item} R
:sync: r

```r
test <- fisher_z(data)  # or kci(data), gcm(data), ...

res <- run_test(test, "X", "Y", "Z")
# res$statistic, res$p_value, res$dof, res$effect_size

is_independent(test, "X", "Y", "Z", significance_level = 0.05)
```

:::

:::{tab-item} JavaScript
:sync: javascript

```javascript
const test = new FisherZ(data); // or new KCI(data), new GCM(data), ...

const result = test.runTest("X", "Y", ["Z"]);
// result.statistic, result.pValue, result.dof, result.effectSize

test.isIndependent("X", "Y", ["Z"], 0.05);
```

:::

:::{tab-item} Rust
:sync: rust

```rust
let test = FisherZ::new(); // or Kci::new(), Gcm::new(), ...

let result = test.test(&data, x, y, &[z])?;
// result.statistic, result.p_value, result.dof, result.effect_size

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

CI Tests <tests/index>
Benchmark <benchmark>
API reference <api>
```
