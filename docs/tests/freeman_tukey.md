---
myst:
  html_meta:
    description: The Freeman-Tukey power-divergence conditional independence test in FastCIT, with examples for Python, R, JavaScript and Rust.
---

# Freeman-Tukey test

:Data types: X, Y and Z must be discrete.

## Usage

::::{tab-set}
:sync-group: language

:::{tab-item} Python
:sync: python

`fastcit.FreemanTukey(data, yates=True)`

```{literalinclude} ../../crates/ci-python/examples/freeman_tukey.py
:language: python
```

:::

:::{tab-item} R
:sync: r

`freeman_tukey(data, yates = TRUE)`

```{literalinclude} ../../crates/ci-r/inst/examples/tests/freeman_tukey.R
:language: r
```

:::

:::{tab-item} JavaScript
:sync: javascript

`new FreemanTukey(data, { yates: true })`

```{literalinclude} ../../crates/ci-js/examples/freeman_tukey.js
:language: javascript
```

:::

:::{tab-item} Rust
:sync: rust

`fastcit_core::ci_tests::FreemanTukey { yates: true }`

```{literalinclude} ../../crates/ci-core/examples/freeman_tukey.rs
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
\mathrm{FT} &= 8 \sum_{z} \sum_{i,j} \left( O_{ij} - \sqrt{O_{ij} \, E_{ij}} \right) \\
&= 4 \sum_{z} \sum_{i,j} \left( \sqrt{O_{ij}} - \sqrt{E_{ij}} \right)^2, \\
\mathrm{dof} &= \sum_{z} \left(r_z - 1\right)\left(c_z - 1\right), \\
p &= P\left(\chi^2_{\mathrm{dof}} \geq \mathrm{FT}\right).
\end{aligned}
$$

$r_z$ and $c_z$ are the numbers of X and Y categories in table $z$.
The two forms of FT are equal, because a table has the same sum of $O$ and of $E$.
With `yates` on, a 2 × 2 table uses $O'_{ij} = O_{ij} - \operatorname{clip}\left(O_{ij} - E_{ij}, -0.5, 0.5\right)$.
The effect size is Cramér's V, $\sqrt{\max\left(\mathrm{FT}, 0\right) / \left(n \left(k - 1\right)\right)}$.
$n$ is the number of rows, and $k$ is the smaller number of X and Y categories.
