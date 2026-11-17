---
myst:
  html_meta:
    description: The modified log-likelihood ratio conditional independence test in FastCIT, with examples for Python, R, JavaScript and Rust.
---

# Modified log-likelihood test

:Data types: X, Y and Z must be discrete.
:API: All tests use the same API. See [one API for all tests](../index.md#one-api-for-all-tests).

## Usage

::::{tab-set}
:sync-group: language

:::{tab-item} Python
:sync: python

`fastcit.ModifiedLikelihood(data, yates=True)`

```{literalinclude} ../../crates/ci-python/examples/modified_likelihood.pycon
:language: pycon
```

:::

:::{tab-item} R
:sync: r

`modified_likelihood(data, yates = TRUE)`

```{literalinclude} ../../crates/ci-r/inst/examples/tests/modified_likelihood.R
:language: r
```

:::

:::{tab-item} JavaScript
:sync: javascript

`new ModifiedLikelihood(data, { yates: true })`

```{literalinclude} ../../crates/ci-js/examples/modified_likelihood.js
:language: javascript
```

:::

:::{tab-item} Rust
:sync: rust

`fastcit_core::ci_tests::ModifiedLikelihood { yates: true }`

```{literalinclude} ../../crates/ci-core/examples/modified_likelihood.rs
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
G_M^2 &= 2 \sum_{z} \sum_{i,j} E_{ij} \ln \frac{E_{ij}}{O_{ij}}, \\
\mathrm{dof} &= \sum_{z} \left(r_z - 1\right)\left(c_z - 1\right), \\
p &= P\left(\chi^2_{\mathrm{dof}} \geq G_M^2\right).
\end{aligned}
$$

$r_z$ and $c_z$ are the numbers of X and Y categories in table $z$.
A cell with $O_{ij} = 0$ makes $G_M^2$ infinite, and then $p = 0$.
Yates' correction prevents this in a 2 × 2 table.
With `yates` on, a 2 × 2 table uses $O'_{ij} = O_{ij} - \operatorname{clip}\left(O_{ij} - E_{ij}, -0.5, 0.5\right)$.
The effect size is Cramér's V, $\sqrt{G_M^2 / \left(n \left(k - 1\right)\right)}$.
$n$ is the number of rows in the data, and $k$ is the smaller of the numbers of X and Y categories in the data.
