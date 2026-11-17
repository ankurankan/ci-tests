---
myst:
  html_meta:
    description: The Freeman-Tukey power-divergence conditional independence test in FastCIT, with parameters and examples for Python, R, JavaScript and Rust.
---

# Freeman-Tukey test

:Data type: Discrete
:Python and JavaScript: `FreemanTukey`
:R: `freeman_tukey()`
:Rust: `fastcit_core::ci_tests::FreemanTukey`

The Freeman-Tukey test checks whether two discrete variables X and Y are independent given a set Z of discrete variables.
It compares the square roots of the observed counts with the square roots of the counts that independence predicts.

## When to use

- X, Y and all the variables in Z are discrete, for example categories or integer codes.
- You want the power-divergence statistic with $\lambda = -1/2$.
- Most expected counts in each table are 5 or more. With smaller counts, the chi-squared approximation of the p-value is less accurate.
- For sparse tables, compare the result with the other power-divergence tests: {doc}`chi_squared`, {doc}`log_likelihood`, {doc}`cressie_read` and {doc}`modified_likelihood`.

## Usage and parameters

Select your language.
Each tab shows the constructor, its parameters and an example.
The CI of each language runs the example file.

::::{tab-set}
:sync-group: language

:::{tab-item} Python
:sync: python

`fastcit.FreemanTukey(data, yates=True)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `data` | `fastcit.Dataset`, `dict` or `pandas.DataFrame` | Required | The data. X, Y and the columns in Z must be discrete. A `DataFrame` gives integer, boolean, categorical and string columns the discrete kind. |
| `yates` | `bool` | `True` | Apply Yates' continuity correction to each 2 × 2 table. |

| Method | Returns |
|---|---|
| `run_test(x, y, z=None)` | A `CiResult` with `statistic`, `p_value`, `dof` and `effect_size` (Cramér's V). |
| `is_independent(x, y, z=None, significance_level=0.05)` | `True` when `p_value >= significance_level`. |

`x` and `y` are column names or column indices. `z` is a list of column names or indices.

```{literalinclude} ../../crates/ci-python/examples/freeman_tukey.py
:language: python
:caption: crates/ci-python/examples/freeman_tukey.py
```

:::

:::{tab-item} R
:sync: r

`freeman_tukey(data, yates = TRUE)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `data` | `fastcit_dataset` from `dataset()`, or a `data.frame` | Required | The data. X, Y and the columns in Z must be discrete. Integer, factor, character and logical columns are discrete. |
| `yates` | `logical` | `TRUE` | Apply Yates' continuity correction to each 2 × 2 table. |

| Function | Returns |
|---|---|
| `run_test(test, x, y, z = character())` | A list with `statistic`, `p_value`, `dof` and `effect_size` (Cramér's V). |
| `is_independent(test, x, y, z = character(), significance_level = 0.05)` | `TRUE` when `p_value >= significance_level`. |

`x` and `y` are column names. `z` is a character vector of column names.

```{literalinclude} ../../crates/ci-r/inst/examples/tests/freeman_tukey.R
:language: r
:caption: crates/ci-r/inst/examples/tests/freeman_tukey.R
```

:::

:::{tab-item} JavaScript
:sync: javascript

`new FreemanTukey(data, options)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `data` | `Dataset`, or an object `{ name: { kind, values } }` | Required | The data. X, Y and the columns in Z must have `kind: "discrete"`. |
| `options.yates` | `boolean` | `true` | Apply Yates' continuity correction to each 2 × 2 table. |

| Method | Returns |
|---|---|
| `runTest(x, y, z)` | An object `{ statistic, pValue, dof, effectSize }`. `effectSize` is Cramér's V. |
| `isIndependent(x, y, z, significanceLevel = 0.05)` | `true` when `pValue >= significanceLevel`. |

`x` and `y` are column names. `z` is an array of column names. Use `[]` for an empty Z.

```{literalinclude} ../../crates/ci-js/examples/freeman_tukey.js
:language: javascript
:caption: crates/ci-js/examples/freeman_tukey.js
```

:::

:::{tab-item} Rust
:sync: rust

`fastcit_core::ci_tests::FreemanTukey { yates: bool }`

| Field | Type | `FreemanTukey::new()` | Description |
|---|---|---|---|
| `yates` | `bool` | `true` | Apply Yates' continuity correction to each 2 × 2 table. |

| Method (trait `CITest`) | Returns |
|---|---|
| `test(&data, x, y, &z)` | `Result<CiResult, CiError>`. `CiResult` has `statistic`, `p_value`, `dof` and `effect_size` (Cramér's V). |
| `is_independent(&data, x, y, &z, alpha)` | `Result<bool, CiError>`: `true` when `p_value >= alpha`. |

`x` and `y` are column indices. `z` is a slice of column indices. Get an index with `data.index_of(name)`.

```{literalinclude} ../../crates/ci-core/examples/freeman_tukey.rs
:language: rust
:caption: crates/ci-core/examples/freeman_tukey.rs
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

**Statistic.**
The statistic is the power-divergence statistic with $\lambda = -1/2$ (see {doc}`cressie_read`), summed over the strata:

$$
\begin{aligned}
\mathrm{FT} &= 8 \sum_{z} \sum_{i,j} \left( O_{ij} - \sqrt{O_{ij} \, E_{ij}} \right) \\
&= 4 \sum_{z} \sum_{i,j} \left( \sqrt{O_{ij}} - \sqrt{E_{ij}} \right)^2.
\end{aligned}
$$

FastCIT calculates the first form.
The two forms are equal, because the observed and expected counts of a table have the same sum.
Yates' correction does not change this sum.
This is the Freeman-Tukey statistic of Cressie and Read (1984).
FastCIT does not calculate the statistic $\sum \left( \sqrt{O} + \sqrt{O + 1} - \sqrt{4E + 1} \right)^2$, which uses the transform of Freeman and Tukey (1950).

**Degrees of freedom.**
Each stratum adds $(r_z - 1)(c_z - 1)$, where $r_z$ and $c_z$ are the numbers of X and Y categories in the stratum.
A stratum with fewer than two X categories or fewer than two Y categories adds nothing to the statistic or to the degrees of freedom.

**p-value.**
The p-value is $P\left(\chi^2_{\mathrm{dof}} \geq \mathrm{FT}\right)$, from the chi-squared distribution.
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
V = \sqrt{\frac{\max\left(\mathrm{FT}, 0\right)}{n \, (k - 1)}},
$$

where $n$ is the number of rows and $k$ is the smaller of the numbers of X and Y categories in the data.
FastCIT uses FT in this formula, not Pearson's statistic, so $V$ can be greater than 1.
The maximum with 0 removes a small negative value that rounding can cause.
When $k < 2$, the effect size is empty (`None`, `NULL` or `null`).

**Errors.**
The test returns an error when X, Y or a column in Z is continuous.
It also returns an error when X and Y are the same column, or when Z contains X, Y or a column two times.
A missing value in the data causes an error.

## References

- Freeman, M. F. and Tukey, J. W. (1950). Transformations related to the angular and the square root. *The Annals of Mathematical Statistics*, 21(4), 607–611. <https://doi.org/10.1214/aoms/1177729756>
- Cressie, N. and Read, T. R. C. (1984). Multinomial goodness-of-fit tests. *Journal of the Royal Statistical Society: Series B*, 46(3), 440–464. <https://doi.org/10.1111/j.2517-6161.1984.tb01318.x>
- Yates, F. (1934). Contingency tables involving small numbers and the χ² test. *Supplement to the Journal of the Royal Statistical Society*, 1(2), 217–235. <https://doi.org/10.2307/2983604>
- Cramér, H. (1946). *Mathematical Methods of Statistics*. Princeton University Press.
