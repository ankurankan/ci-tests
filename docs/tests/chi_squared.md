---
myst:
  html_meta:
    description: The chi-squared conditional independence test in FastCIT, with examples for Python, R, JavaScript and Rust.
---

# Chi-squared test

:Data types: X, Y and Z must be discrete.

## Usage

::::{tab-set}
:sync-group: language

:::{tab-item} Python
:sync: python

`fastcit.ChiSquared(data, yates=True)`

```{literalinclude} ../../crates/ci-python/examples/chi_squared.py
:language: python
```

:::

:::{tab-item} R
:sync: r

`chi_squared(data, yates = TRUE)`

```{literalinclude} ../../crates/ci-r/inst/examples/tests/chi_squared.R
:language: r
```

:::

:::{tab-item} JavaScript
:sync: javascript

`new ChiSquared(data, { yates: true })`

```{literalinclude} ../../crates/ci-js/examples/chi_squared.js
:language: javascript
```

:::

:::{tab-item} Rust
:sync: rust

`fastcit_core::ci_tests::ChiSquared { yates: true }`

```{literalinclude} ../../crates/ci-core/examples/chi_squared.rs
:language: rust
```

:::
::::

## Method

Each combination $z$ of Z values gives one table.
$O_{ij}$ is the number of rows with $X = i$ and $Y = j$.
$R_i$ and $C_j$ are the row and column sums, and $n_z$ is the number of rows.

$$
\begin{aligned}
E_{ij} &= \frac{R_i \, C_j}{n_z}, \\
\chi^2 &= \sum_{z} \sum_{i,j} \frac{\left(O_{ij} - E_{ij}\right)^2}{E_{ij}}, \\
\mathrm{dof} &= \sum_{z} \left(r_z - 1\right)\left(c_z - 1\right), \\
p &= P\left(\chi^2_{\mathrm{dof}} \geq \chi^2\right).
\end{aligned}
$$

$r_z$ and $c_z$ are the numbers of X and Y categories in table $z$.
With `yates` on, a 2 × 2 table uses $O'_{ij} = O_{ij} - \operatorname{clip}\left(O_{ij} - E_{ij}, -0.5, 0.5\right)$.
The effect size is Cramér's V, $\sqrt{\chi^2 / \left(n \left(k - 1\right)\right)}$.
$n$ is the number of rows, and $k$ is the smaller number of X and Y categories.
