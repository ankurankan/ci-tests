---
myst:
  html_meta:
    description: The log-likelihood ratio (G-test) conditional independence test in FastCIT, with examples for Python, R, JavaScript and Rust.
---

# Log-likelihood test

:Data types: X, Y and Z must be discrete.

## Usage

::::{tab-set}
:sync-group: language

:::{tab-item} Python
:sync: python

`fastcit.LogLikelihood(data, yates=True)`

```{literalinclude} ../../crates/ci-python/examples/log_likelihood.py
:language: python
```

:::

:::{tab-item} R
:sync: r

`log_likelihood(data, yates = TRUE)`

```{literalinclude} ../../crates/ci-r/inst/examples/tests/log_likelihood.R
:language: r
```

:::

:::{tab-item} JavaScript
:sync: javascript

`new LogLikelihood(data, { yates: true })`

```{literalinclude} ../../crates/ci-js/examples/log_likelihood.js
:language: javascript
```

:::

:::{tab-item} Rust
:sync: rust

`fastcit_core::ci_tests::LogLikelihood { yates: true }`

```{literalinclude} ../../crates/ci-core/examples/log_likelihood.rs
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
G^2 &= 2 \sum_{z} \sum_{i,j} O_{ij} \ln \frac{O_{ij}}{E_{ij}}, \\
\mathrm{dof} &= \sum_{z} \left(r_z - 1\right)\left(c_z - 1\right), \\
p &= P\left(\chi^2_{\mathrm{dof}} \geq G^2\right).
\end{aligned}
$$

$r_z$ and $c_z$ are the numbers of X and Y categories in table $z$.
A cell with $O_{ij} = 0$ adds 0 to $G^2$.
With `yates` on, a 2 × 2 table uses $O'_{ij} = O_{ij} - \operatorname{clip}\left(O_{ij} - E_{ij}, -0.5, 0.5\right)$.
The effect size is Cramér's V, $\sqrt{\max\left(G^2, 0\right) / \left(n \left(k - 1\right)\right)}$.
$n$ is the number of rows, and $k$ is the smaller number of X and Y categories.
