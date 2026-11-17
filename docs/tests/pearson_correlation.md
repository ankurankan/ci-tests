---
myst:
  html_meta:
    description: The Pearson (partial) correlation conditional independence test in FastCIT, with examples for Python, R, JavaScript and Rust.
---

# Pearson correlation test

:Data types: X, Y and Z must be continuous.

## Usage

::::{tab-set}
:sync-group: language

:::{tab-item} Python
:sync: python

`fastcit.PearsonCorrelation(data)`

```{literalinclude} ../../crates/ci-python/examples/pearson_correlation.py
:language: python
```

:::

:::{tab-item} R
:sync: r

`pearson_correlation(data)`

```{literalinclude} ../../crates/ci-r/inst/examples/tests/pearson_correlation.R
:language: r
```

:::

:::{tab-item} JavaScript
:sync: javascript

`new PearsonCorrelation(data)`

```{literalinclude} ../../crates/ci-js/examples/pearson_correlation.js
:language: javascript
```

:::

:::{tab-item} Rust
:sync: rust

`fastcit_core::ci_tests::PearsonCorrelation::new()`

```{literalinclude} ../../crates/ci-core/examples/pearson_correlation.rs
:language: rust
```

:::
::::

## Method

FastCIT regresses X and Y on $[1, Z]$ with ordinary least squares.
$r$ is the Pearson correlation of the two residual vectors, and $n$ is the number of rows.

$$
\begin{aligned}
\mathrm{dof} &= n - |Z| - 2, \\
t &= r \sqrt{\frac{\mathrm{dof}}{1 - r^2}}, \\
p &= 2 \, P\left(T_{\mathrm{dof}} \geq |t|\right).
\end{aligned}
$$

$T_{\mathrm{dof}}$ has Student's t-distribution.
The statistic is $r$, not $t$.
The effect size is $|r|$.
