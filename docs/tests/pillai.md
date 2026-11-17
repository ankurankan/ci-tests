---
myst:
  html_meta:
    description: The Pillai's trace conditional independence test for mixed data in FastCIT, with parameters and examples for Python, R, JavaScript and Rust.
---

# Pillai's trace test

:Data type: Mixed (discrete and continuous)
:Python and JavaScript: `PillaiTrace`
:R: `pillai()`
:Rust: `fastcit_core::ci_tests::Pillai`

The Pillai's trace test checks whether two variables X and Y are independent given a set Z.
X, Y and each variable in Z can be discrete or continuous.
The test regresses X and Y on Z and tests the canonical correlations of the residuals.

## When to use

- Your data has discrete and continuous variables.
- The effect of Z on X and on Y is approximately linear. FastCIT uses linear regression, and it has no option for other regression methods.
- pgmpy's `PillaiTrace` uses a random forest by default. So its results can differ from the results of FastCIT.
- With continuous X and Y and an empty Z, the p-value is the p-value of the {doc}`pearson_correlation`.
- With a discrete X, a continuous Y and an empty Z, the test is the one-way ANOVA F-test.

## Usage and parameters

Select your language.
Each tab shows the constructor, its parameters and an example.
The CI of each language runs the example file.

::::{tab-set}
:sync-group: language

:::{tab-item} Python
:sync: python

`fastcit.PillaiTrace(data)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `data` | `fastcit.Dataset`, `dict` or `pandas.DataFrame` | Required | The data. X, Y and the columns in Z can be discrete or continuous. A `DataFrame` gives floating-point columns the continuous kind, and integer, boolean, categorical and string columns the discrete kind. |

| Method | Returns |
|---|---|
| `run_test(x, y, z=None)` | A `CiResult` with `statistic` (Pillai's trace V), `p_value`, `dof` (`None`) and `effect_size` (partial eta squared). |
| `is_independent(x, y, z=None, significance_level=0.05)` | `True` when `p_value >= significance_level`. |

`x` and `y` are column names or column indices. `z` is a list of column names or indices.

```{literalinclude} ../../crates/ci-python/examples/pillai.py
:language: python
:caption: crates/ci-python/examples/pillai.py
```

:::

:::{tab-item} R
:sync: r

`pillai(data)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `data` | `fastcit_dataset` from `dataset()`, or a `data.frame` | Required | The data. X, Y and the columns in Z can be discrete or continuous. Double columns are continuous. Integer, factor, character and logical columns are discrete. |

| Function | Returns |
|---|---|
| `run_test(test, x, y, z = character())` | A list with `statistic` (Pillai's trace V), `p_value`, `dof` (`NULL`) and `effect_size` (partial eta squared). |
| `is_independent(test, x, y, z = character(), significance_level = 0.05)` | `TRUE` when `p_value >= significance_level`. |

`x` and `y` are column names. `z` is a character vector of column names.

```{literalinclude} ../../crates/ci-r/inst/examples/tests/pillai.R
:language: r
:caption: crates/ci-r/inst/examples/tests/pillai.R
```

:::

:::{tab-item} JavaScript
:sync: javascript

`new PillaiTrace(data)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `data` | `Dataset`, or an object `{ name: { kind, values } }` | Required | The data. X, Y and the columns in Z can have `kind: "discrete"` or `kind: "continuous"`. |

The constructor accepts no options.

| Method | Returns |
|---|---|
| `runTest(x, y, z)` | An object `{ statistic, pValue, dof, effectSize }`. `statistic` is Pillai's trace V. `dof` is `null`. `effectSize` is partial eta squared. |
| `isIndependent(x, y, z, significanceLevel = 0.05)` | `true` when `pValue >= significanceLevel`. |

`x` and `y` are column names. `z` is an array of column names. Use `[]` for an empty Z.

```{literalinclude} ../../crates/ci-js/examples/pillai.js
:language: javascript
:caption: crates/ci-js/examples/pillai.js
```

:::

:::{tab-item} Rust
:sync: rust

`fastcit_core::ci_tests::Pillai`

`Pillai` has no fields. Make it with `Pillai::new()` or `Pillai::default()`.

| Method (trait `CITest`) | Returns |
|---|---|
| `test(&data, x, y, &z)` | `Result<CiResult, CiError>`. `CiResult` has `statistic` (Pillai's trace V), `p_value`, `dof` (`None`) and `effect_size` (partial eta squared). |
| `is_independent(&data, x, y, &z, alpha)` | `Result<bool, CiError>`: `true` when `p_value >= alpha`. |

`x` and `y` are column indices. `z` is a slice of column indices. Get an index with `data.index_of(name)`.

```{literalinclude} ../../crates/ci-core/examples/pillai.rs
:language: rust
:caption: crates/ci-core/examples/pillai.rs
```

:::
::::

## Method

**Levels.**
FastCIT numbers the levels of a discrete column in the order in which they first occur in the data.

**Design matrix.**
The design matrix is $[1, Z]$.
A continuous Z column adds its values.
A discrete Z column with $K$ levels adds $K - 1$ indicator columns. FastCIT drops the indicator of the first level.

**Targets.**
A continuous X gives one target column, its values.
A discrete X with $K$ levels gives $K - 1$ indicator columns. FastCIT drops the indicator of the last level.
This is a linear probability model. Y gives its target columns in the same way.

**Residuals.**
FastCIT regresses each target column on $[1, Z]$ with ordinary least squares, with a Householder QR decomposition.
The residuals of X form the $n \times p$ matrix $R_X$, and the residuals of Y form the $n \times q$ matrix $R_Y$.
There are $s = \min(p, q)$ canonical correlations.

**Statistic.**
The statistic is Pillai's trace of the residuals:

$$
V = \sum_{i=1}^{s} \rho_i^2 = \operatorname{tr}\left( S_{XX}^{-1} S_{XY} S_{YY}^{-1} S_{YX} \right),
$$

where $\rho_i$ are the canonical correlations of $R_X$ and $R_Y$.
$S_{XY}$ is the matrix of sums of products of the centred columns of $R_X$ and $R_Y$, and the other $S$ matrices are the same.
FastCIT calculates $V$ exactly with Cholesky factors. It does not use an iterative CCA.

**F approximation.**
FastCIT uses the F approximation of pgmpy:

$$
\begin{aligned}
\mathrm{df}_1 &= p \, q, \\
\mathrm{df}_2 &= s \, (n - 1 + s - p - q), \\
F &= \frac{V}{\mathrm{df}_1} \cdot \frac{\mathrm{df}_2}{s - V}.
\end{aligned}
$$

The p-value is $P\left( F_{\mathrm{df}_1, \mathrm{df}_2} \geq F \right)$, from the F distribution.
$\mathrm{df}_2$ does not count the columns of Z. pgmpy uses the same $\mathrm{df}_2$, and FastCIT keeps it.
With many Z columns or levels compared with $n$, the p-value can be too small.
The test has no degrees of freedom of its own, so `dof` is empty.
`is_independent` returns true when the p-value is greater than or equal to the significance level.

**Perfect dependence.**
FastCIT limits $V$ to at most $s$.
When $s - V \leq 10^{-12} \, s$, the p-value is 0.
The residuals can force $V = s$.
This occurs when Z is not empty.
It also needs $n$ minus the number of columns of $[1, Z]$ to equal the larger of $p$ and $q$.
The p-value is then 0 ("dependent"), as in pgmpy.

**Effect size.**
The effect size is partial eta squared, $V / s$.

**Limits and errors.**
The test needs more rows than $[1, Z]$ has columns.
It returns an error when $\mathrm{df}_2 \leq 0$.
It returns an error when $n$ minus the number of columns of $[1, Z]$ is less than the larger of $p$ and $q$.
It returns an error when a continuous X or Y is constant, or when a discrete X or Y has only one level.
It returns an error when Z explains a target column completely, so that a residual column has no variance.
It returns an error when the residual columns of X, or of Y, are linearly dependent.
It returns an error when the columns of $[1, Z]$ are linearly dependent.
Examples are a constant Z column, or two discrete Z columns with the same groups.
pgmpy fits such a design with least squares.
FastCIT compares each pivot of the QR decomposition with the norm of its column. So the scale of a Z column does not change this decision.
A missing value in the data causes an error.

## References

- Pillai, K. C. S. (1955). Some new test criteria in multivariate analysis. *The Annals of Mathematical Statistics*, 26(1), 117–121. <https://doi.org/10.1214/aoms/1177728599>
- Hotelling, H. (1936). Relations between two sets of variates. *Biometrika*, 28(3/4), 321–377. <https://doi.org/10.2307/2333955>
- Muller, K. E. and Peterson, B. L. (1984). Practical methods for computing power in testing the multivariate general linear hypothesis. *Computational Statistics & Data Analysis*, 2(2), 143–158. <https://doi.org/10.1016/0167-9473(84)90002-1>
- Li, C. and Shepherd, B. E. (2010). Test of association between two ordinal variables while adjusting for covariates. *Journal of the American Statistical Association*, 105(490), 612–620. <https://doi.org/10.1198/jasa.2010.tm09386>
- Ankan, A. and Textor, J. (2023). A simple unified approach to testing high-dimensional conditional independences for categorical and ordinal data. *Proceedings of the AAAI Conference on Artificial Intelligence*, 37(10), 12180–12188. <https://doi.org/10.1609/aaai.v37i10.26436>
