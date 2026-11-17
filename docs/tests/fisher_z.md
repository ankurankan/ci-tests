---
myst:
  html_meta:
    description: The Fisher-z conditional independence test in FastCIT, with examples for Python, R, JavaScript and Rust.
---

# Fisher-z test

:Data types: X, Y and Z must be continuous.
:API: All tests use the same API. See [one API for all tests](../index.md#one-api-for-all-tests).

## Usage

::::{tab-set}
:sync-group: language

:::{tab-item} Python
:sync: python

`fastcit.FisherZ(data)`

```{literalinclude} ../../crates/ci-python/examples/fisher_z.pycon
:language: pycon
```

:::

:::{tab-item} R
:sync: r

`fisher_z(data)`

```{literalinclude} ../../crates/ci-r/inst/examples/tests/fisher_z.R
:language: r
```

:::

:::{tab-item} JavaScript
:sync: javascript

`new FisherZ(data)`

```{literalinclude} ../../crates/ci-js/examples/fisher_z.js
:language: javascript
```

:::

:::{tab-item} Rust
:sync: rust

`fastcit_core::ci_tests::FisherZ::new()`

```{literalinclude} ../../crates/ci-core/examples/fisher_z.rs
:language: rust
```

:::
::::

## Method

FastCIT regresses X and Y on $[1, Z]$ with ordinary least squares.
$r$ is the Pearson correlation of the two residual vectors.
$n$ is the number of rows, and $|Z|$ is the number of columns in Z.

$$
\begin{aligned}
\tilde r &= \operatorname{clip}\left(r, -1 + 10^{-6}, 1 - 10^{-6}\right), \\
z &= \sqrt{n - |Z| - 3}\; \operatorname{atanh}\left(\tilde r\right), \\
p &= 2 \left(1 - \Phi\left(|z|\right)\right).
\end{aligned}
$$

$\Phi$ is the standard normal distribution function.
The effect size is $|r|$, before the clip.
