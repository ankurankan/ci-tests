---
myst:
  html_meta:
    description: The Pillai's trace conditional independence test for mixed data in FastCIT, with examples for Python, R, JavaScript and Rust.
---

# Pillai's trace test

:Data types: X, Y and Z can each be discrete or continuous.
:API: All tests use the same API. See [one API for all tests](../index.md#one-api-for-all-tests).

## Usage

::::{tab-set}
:sync-group: language

:::{tab-item} Python
:sync: python

`fastcit.PillaiTrace(data)`

```{literalinclude} ../../crates/ci-python/examples/pillai.pycon
:language: pycon
```

:::

:::{tab-item} R
:sync: r

`pillai(data)`

```{literalinclude} ../../crates/ci-r/inst/examples/tests/pillai.R
:language: r
```

:::

:::{tab-item} JavaScript
:sync: javascript

`new PillaiTrace(data)`

```{literalinclude} ../../crates/ci-js/examples/pillai.js
:language: javascript
```

:::

:::{tab-item} Rust
:sync: rust

`fastcit_core::ci_tests::Pillai::new()`

```{literalinclude} ../../crates/ci-core/examples/pillai.rs
:language: rust
```

:::
::::

## Method

A continuous column gives one column of values.
A discrete column with $K$ levels gives $K - 1$ indicator columns.
FastCIT regresses the $p$ columns of X and the $q$ columns of Y on $[1, Z]$ with ordinary least squares.
$\rho_i$ are the canonical correlations of the residuals, $s = \min(p, q)$, and $n$ is the number of rows.

$$
\begin{aligned}
V &= \sum_{i=1}^{s} \rho_i^2, \\
\mathrm{df}_1 &= p \, q, \\
\mathrm{df}_2 &= s \, (n - 1 + s - p - q), \\
F &= \frac{V}{\mathrm{df}_1} \cdot \frac{\mathrm{df}_2}{s - V}, \\
p\text{-value} &= P\left( F_{\mathrm{df}_1, \mathrm{df}_2} \geq F \right).
\end{aligned}
$$

$\mathrm{df}_2$ does not count the columns of Z.
When $s - V \leq 10^{-12} \, s$, the p-value is 0.
The effect size is partial eta squared, $V / s$.
