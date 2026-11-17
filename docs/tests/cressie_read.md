---
myst:
  html_meta:
    description: The Cressie-Read power-divergence conditional independence test in FastCIT, with parameters and examples for Python, R, JavaScript and Rust.
---

# Cressie-Read test

:Data type: Discrete
:Python and JavaScript: `CressieRead`
:R: `cressie_read()`
:Rust: `fastcit_core::ci_tests::CressieRead`

The Cressie-Read test checks whether two discrete variables X and Y are independent given a set Z of discrete variables.
It compares the observed counts with the counts that independence predicts, with the power-divergence statistic for $\lambda = 2/3$.

## When to use

- X, Y and all the variables in Z are discrete, for example categories or integer codes.
- You want the statistic that Cressie and Read (1984) recommend. It is a compromise between Pearson's statistic ($\lambda = 1$) and the log-likelihood ratio ($\lambda = 0$).
- Most expected counts in each table are 5 or more. With smaller counts, the chi-squared approximation of the p-value is less accurate.
- For sparse tables, compare the result with the other power-divergence tests: {doc}`chi_squared`, {doc}`log_likelihood`, {doc}`freeman_tukey` and {doc}`modified_likelihood`.

## Usage and parameters

Select your language.
Each tab shows the constructor, its parameters and an example.
The CI of each language runs the example file.

::::{tab-set}
:sync-group: language

:::{tab-item} Python
:sync: python

`fastcit.CressieRead(data, yates=True)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `data` | `fastcit.Dataset`, `dict` or `pandas.DataFrame` | Required | The data. X, Y and the columns in Z must be discrete. A `DataFrame` gives integer, boolean, categorical and string columns the discrete kind. |
| `yates` | `bool` | `True` | Apply Yates' continuity correction to each 2 × 2 table. |

| Method | Returns |
|---|---|
| `run_test(x, y, z=None)` | A `CiResult` with `statistic`, `p_value`, `dof` and `effect_size` (Cramér's V). |
| `is_independent(x, y, z=None, significance_level=0.05)` | `True` when `p_value >= significance_level`. |

`x` and `y` are column names or column indices. `z` is a list of column names or indices.

```{literalinclude} ../../crates/ci-python/examples/cressie_read.py
:language: python
:caption: crates/ci-python/examples/cressie_read.py
```

:::

:::{tab-item} R
:sync: r

`cressie_read(data, yates = TRUE)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `data` | `fastcit_dataset` from `dataset()`, or a `data.frame` | Required | The data. X, Y and the columns in Z must be discrete. Integer, factor, character and logical columns are discrete. |
| `yates` | `logical` | `TRUE` | Apply Yates' continuity correction to each 2 × 2 table. |

| Function | Returns |
|---|---|
| `run_test(test, x, y, z = character())` | A list with `statistic`, `p_value`, `dof` and `effect_size` (Cramér's V). |
| `is_independent(test, x, y, z = character(), significance_level = 0.05)` | `TRUE` when `p_value >= significance_level`. |

`x` and `y` are column names. `z` is a character vector of column names.

```{literalinclude} ../../crates/ci-r/inst/examples/tests/cressie_read.R
:language: r
:caption: crates/ci-r/inst/examples/tests/cressie_read.R
```

:::

:::{tab-item} JavaScript
:sync: javascript

`new CressieRead(data, options)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `data` | `Dataset`, or an object `{ name: { kind, values } }` | Required | The data. X, Y and the columns in Z must have `kind: "discrete"`. |
| `options.yates` | `boolean` | `true` | Apply Yates' continuity correction to each 2 × 2 table. |

| Method | Returns |
|---|---|
| `runTest(x, y, z)` | An object `{ statistic, pValue, dof, effectSize }`. `effectSize` is Cramér's V. |
| `isIndependent(x, y, z, significanceLevel = 0.05)` | `true` when `pValue >= significanceLevel`. |

`x` and `y` are column names. `z` is an array of column names. Use `[]` for an empty Z.

```{literalinclude} ../../crates/ci-js/examples/cressie_read.js
:language: javascript
:caption: crates/ci-js/examples/cressie_read.js
```

:::

:::{tab-item} Rust
:sync: rust

`fastcit_core::ci_tests::CressieRead { yates: bool }`

| Field | Type | `CressieRead::new()` | Description |
|---|---|---|---|
| `yates` | `bool` | `true` | Apply Yates' continuity correction to each 2 × 2 table. |

| Method (trait `CITest`) | Returns |
|---|---|
| `test(&data, x, y, &z)` | `Result<CiResult, CiError>`. `CiResult` has `statistic`, `p_value`, `dof` and `effect_size` (Cramér's V). |
| `is_independent(&data, x, y, &z, alpha)` | `Result<bool, CiError>`: `true` when `p_value >= alpha`. |

`x` and `y` are column indices. `z` is a slice of column indices. Get an index with `data.index_of(name)`.

```{literalinclude} ../../crates/ci-core/examples/cressie_read.rs
:language: rust
:caption: crates/ci-core/examples/cressie_read.rs
```

:::
::::

## Method

**Strata.**
FastCIT splits the rows into strata: one stratum for each combination of Z values in the data.
With an empty Z, all rows are one stratum.

**Table.**
In stratum $z$ with $n_z$ rows, $O_{ij}$ is the number of rows with $X = i$ and $Y = j$.
FastCIT removes the categories of X and Y that have no rows in the stratum.
$R_i$ and $C_j$ are the row and column sums.
The expected count under independence is

$$
E_{ij} = \frac{R_i \, C_j}{n_z}.
$$

**Power divergence.**
For a parameter $\lambda$, the power-divergence statistic is the sum over the strata of

$$
\frac{2}{\lambda(\lambda + 1)} \sum_{i,j} \left( \frac{O_{ij}^{\lambda + 1}}{E_{ij}^{\lambda}} - O_{ij} \right).
$$

Cressie and Read (1984) write the sum as $\sum O_{ij} \left[ (O_{ij} / E_{ij})^{\lambda} - 1 \right]$.
FastCIT uses the form above, because it gives 0 for a cell with $O_{ij} = 0$ when $\lambda > -1$.
FastCIT has five tests from this family. They differ only in $\lambda$:

| Test | $\lambda$ | Statistic of one table |
|---|---|---|
| {doc}`chi_squared` | 1 | $\sum (O - E)^2 / E$ |
| Cressie-Read (this test) | 2/3 | $\frac{9}{5} \sum \left( O^{5/3} / E^{2/3} - O \right)$ |
| {doc}`log_likelihood` | 0 | $2 \sum O \ln(O / E)$ |
| {doc}`freeman_tukey` | −1/2 | $4 \sum \left( \sqrt{O} - \sqrt{E} \right)^2$ |
| {doc}`modified_likelihood` | −1 | $2 \sum E \ln(E / O)$ |

For $\lambda = 0$ and $\lambda = -1$, the general formula has no value. FastCIT uses its limits there.

**Statistic.**
This test uses $\lambda = 2/3$.
The factor $2 / (\lambda(\lambda + 1))$ is then $9/5$, and the statistic is

$$
\mathrm{CR} = \frac{9}{5} \sum_{z} \sum_{i,j} \left( \frac{O_{ij}^{5/3}}{E_{ij}^{2/3}} - O_{ij} \right).
$$

**Degrees of freedom.**
Each stratum adds $(r_z - 1)(c_z - 1)$, where $r_z$ and $c_z$ are the numbers of X and Y categories in the stratum.
A stratum with fewer than two X categories or fewer than two Y categories adds nothing to the statistic or to the degrees of freedom.

**p-value.**
The p-value is $P\left(\chi^2_{\mathrm{dof}} \geq \mathrm{CR}\right)$, from the chi-squared distribution.
When no stratum adds degrees of freedom, the degrees of freedom are 0 and the p-value is 1.
`is_independent` returns true when the p-value is greater than or equal to the significance level.

**Yates' correction.**
When `yates` is on, FastCIT changes each 2 × 2 table before it calculates the statistic.
It moves each observed count toward its expected count by at most 0.5:

$$
O'_{ij} = O_{ij} - \operatorname{clip}\left(O_{ij} - E_{ij}, -0.5, 0.5\right).
$$

FastCIT then uses $O'_{ij}$ in place of $O_{ij}$ in the statistic.
This is the correction of `scipy.stats.chi2_contingency(correction=True)`, which also applies it for every $\lambda$.
Tables with more than one degree of freedom do not change.
`yates` is on by default in all four languages.

**Effect size.**
The effect size is Cramér's V, calculated from the statistic:

$$
V = \sqrt{\frac{\max\left(\mathrm{CR}, 0\right)}{n \, (k - 1)}},
$$

where $n$ is the number of rows and $k$ is the smaller of the numbers of X and Y categories in the data.
FastCIT uses CR in this formula, not Pearson's statistic, so $V$ can be greater than 1.
The maximum with 0 removes a small negative value that rounding can cause, for example when $O = E$ in all cells.
When $k < 2$, the effect size is empty (`None`, `NULL` or `null`).

**Errors.**
The test returns an error when X, Y or a column in Z is continuous.
It also returns an error when X and Y are the same column, or when Z contains X, Y or a column two times.
A missing value in the data causes an error.

## References

- Cressie, N. and Read, T. R. C. (1984). Multinomial goodness-of-fit tests. *Journal of the Royal Statistical Society: Series B*, 46(3), 440–464. <https://doi.org/10.1111/j.2517-6161.1984.tb01318.x>
- Yates, F. (1934). Contingency tables involving small numbers and the χ² test. *Supplement to the Journal of the Royal Statistical Society*, 1(2), 217–235. <https://doi.org/10.2307/2983604>
- Cramér, H. (1946). *Mathematical Methods of Statistics*. Princeton University Press.
