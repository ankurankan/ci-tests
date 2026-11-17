---
myst:
  html_meta:
    description: The generalised covariance measure (GCM) conditional independence test in FastCIT, with examples for Python, R, JavaScript and Rust.
---

# GCM test

:Data types: X, Y and Z must be continuous.

## Usage

::::{tab-set}
:sync-group: language

:::{tab-item} Python
:sync: python

`fastcit.GCM(data)`

```{literalinclude} ../../crates/ci-python/examples/gcm.py
:language: python
```

:::

:::{tab-item} R
:sync: r

`gcm(data)`

```{literalinclude} ../../crates/ci-r/inst/examples/tests/gcm.R
:language: r
```

:::

:::{tab-item} JavaScript
:sync: javascript

`new GCM(data)`

```{literalinclude} ../../crates/ci-js/examples/gcm.js
:language: javascript
```

:::

:::{tab-item} Rust
:sync: rust

`fastcit_core::ci_tests::Gcm::new()`

```{literalinclude} ../../crates/ci-core/examples/gcm.rs
:language: rust
```

:::
::::

## Method

FastCIT regresses X and Y on $[1, Z]$ with ordinary least squares.
$r_X$ and $r_Y$ are the residuals, $n$ is the number of rows, and $R_i = r_{X,i} \, r_{Y,i}$.

$$
\begin{aligned}
\hat\sigma_R &= \sqrt{\frac{1}{n} \sum_{i} \left( R_i - \bar R \right)^2}, \\
T &= \frac{\sum_{i} R_i}{\sqrt{n} \, \hat\sigma_R}, \\
p &= 2 \left( 1 - \Phi\left( |T| \right) \right).
\end{aligned}
$$

$\hat\sigma_R$ divides by $n$, not by $n - 1$.
$\Phi$ is the standard normal distribution function.
The effect size is the absolute Pearson correlation of $r_X$ and $r_Y$.
