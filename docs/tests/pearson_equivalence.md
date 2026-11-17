---
myst:
  html_meta:
    description: The Pearson equivalence (TOST) conditional independence test in FastCIT, with examples for Python, R, JavaScript and Rust.
---

# Pearson equivalence test

:Data types: X, Y and Z must be continuous.
:API: All tests use the same API. See [one API for all tests](../index.md#one-api-for-all-tests).

## Usage

::::{tab-set}
:sync-group: language

:::{tab-item} Python
:sync: python

`fastcit.PearsonEquivalence(data, delta_threshold=0.1)`

```{literalinclude} ../../crates/ci-python/examples/pearson_equivalence.py
:language: python
```

:::

:::{tab-item} R
:sync: r

`pearson_equivalence(data, delta_threshold = 0.1)`

```{literalinclude} ../../crates/ci-r/inst/examples/tests/pearson_equivalence.R
:language: r
```

:::

:::{tab-item} JavaScript
:sync: javascript

`new PearsonEquivalence(data, { deltaThreshold: 0.1 })`

```{literalinclude} ../../crates/ci-js/examples/pearson_equivalence.js
:language: javascript
```

:::

:::{tab-item} Rust
:sync: rust

`fastcit_core::ci_tests::PearsonEquivalence::new(0.1)`

```{literalinclude} ../../crates/ci-core/examples/pearson_equivalence.rs
:language: rust
```

:::
::::

## Method

FastCIT regresses X and Y on $[1, Z]$ with ordinary least squares.
$r$ is the Pearson correlation of the two residual vectors.
$n$ is the number of rows, and $|Z|$ is the number of columns in Z.

The test checks $H_0: |\rho| \geq \delta$ against $H_1: |\rho| < \delta$.
$\rho$ is the partial correlation in the population, and $\delta$ is `delta_threshold`.

$$
\begin{aligned}
z_r &= \operatorname{atanh}\left(\operatorname{clip}\left(r, -1 + 10^{-6}, 1 - 10^{-6}\right)\right), \\
c &= \sqrt{n - |Z| - 3}, \\
p_{\mathrm{lower}} &= 1 - \Phi\left(c \, (z_r + \operatorname{atanh}(\delta))\right), \\
p_{\mathrm{upper}} &= \Phi\left(c \, (z_r - \operatorname{atanh}(\delta))\right), \\
p &= \max\left(p_{\mathrm{lower}}, p_{\mathrm{upper}}\right).
\end{aligned}
$$

The statistic is $z_r$.
`is_independent` returns true when $p$ is less than the significance level.
This rule is the opposite of the rule of the other tests.
The effect size is $|r|$, before the clip.
