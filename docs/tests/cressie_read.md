---
myst:
  html_meta:
    description: The Cressie-Read power-divergence conditional independence test in FastCIT, with examples for Python, R, JavaScript and Rust.
---

# Cressie-Read test

:Data types: X, Y and Z must be discrete.
:API: All tests use the same API. See [one API for all tests](../index.md#one-api-for-all-tests).

## Usage

::::{tab-set}
:sync-group: language

:::{tab-item} Python
:sync: python

`fastcit.CressieRead(data, yates=True)`

```{literalinclude} ../../crates/ci-python/examples/cressie_read.pycon
:language: pycon
```

:::

:::{tab-item} R
:sync: r

`cressie_read(data, yates = TRUE)`

```{literalinclude} ../../crates/ci-r/inst/examples/tests/cressie_read.R
:language: r
```

:::

:::{tab-item} JavaScript
:sync: javascript

`new CressieRead(data, { yates: true })`

```{literalinclude} ../../crates/ci-js/examples/cressie_read.js
:language: javascript
```

:::

:::{tab-item} Rust
:sync: rust

`fastcit_core::ci_tests::CressieRead { yates: true }`

```{literalinclude} ../../crates/ci-core/examples/cressie_read.rs
:language: rust
```

:::
::::

## Method

Each combination $z$ of Z values gives one table.
$O_{ij}$ is the number of rows with $X = i$ and $Y = j$.
$R_i$ and $C_j$ are the row and column sums, and $n_z$ is the sum of all counts in table $z$.

$$
\begin{aligned}
E_{ij} &= \frac{R_i \, C_j}{n_z}, \\
\mathrm{CR} &= \frac{9}{5} \sum_{z} \sum_{i,j} \left( \frac{O_{ij}^{5/3}}{E_{ij}^{2/3}} - O_{ij} \right), \\
\mathrm{dof} &= \sum_{z} \left(r_z - 1\right)\left(c_z - 1\right), \\
p &= P\left(\chi^2_{\mathrm{dof}} \geq \mathrm{CR}\right).
\end{aligned}
$$

$r_z$ and $c_z$ are the numbers of X and Y categories in table $z$.
This is the power-divergence statistic with $\lambda = 2/3$.
With `yates` on, a 2 × 2 table uses $O'_{ij} = O_{ij} - \operatorname{clip}\left(O_{ij} - E_{ij}, -0.5, 0.5\right)$.
The effect size is Cramér's V, $\sqrt{\mathrm{CR} / \left(n \left(k - 1\right)\right)}$.
$n$ is the number of rows in the data, and $k$ is the smaller of the numbers of X and Y categories in the data.
