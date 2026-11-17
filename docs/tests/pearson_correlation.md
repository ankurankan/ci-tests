---
myst:
  html_meta:
    description: The Pearson (partial) correlation conditional independence test in FastCIT, with parameters and examples for Python, R, JavaScript and Rust.
---

# Pearson correlation test

:Data type: Continuous
:Python and JavaScript: `PearsonCorrelation`
:R: `pearson_correlation()`
:Rust: `fastcit_core::ci_tests::PearsonCorrelation`

The Pearson correlation test checks whether two continuous variables X and Y are independent given a set Z of continuous variables.
It tests the partial correlation of X and Y given Z with a t-test.

## When to use

- X, Y and all the variables in Z are continuous.
- The relations between the variables are approximately linear, and the noise is approximately Gaussian.
- You have few rows. For Gaussian data, the t-distribution of the test is exact, also for small samples.
- The test finds only linear dependence. For nonlinear dependence, use {doc}`kci` or, without Z, {doc}`hsic`.
- {doc}`fisher_z` tests the same partial correlation with a normal approximation. With many rows, the two tests give almost the same p-value.

## Usage and parameters

Select your language.
Each tab shows the constructor, its parameters and an example.
The CI of each language runs the example file.

::::{tab-set}
:sync-group: language

:::{tab-item} Python
:sync: python

`fastcit.PearsonCorrelation(data)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `data` | `fastcit.Dataset`, `dict` or `pandas.DataFrame` | Required | The data. X, Y and the columns in Z must be continuous. A `DataFrame` gives floating-point columns the continuous kind. |

| Method | Returns |
|---|---|
| `run_test(x, y, z=None)` | A `CiResult` with `statistic` (the partial correlation r), `p_value`, `dof` (the degrees of freedom of the t-test) and `effect_size` (the absolute partial correlation). |
| `is_independent(x, y, z=None, significance_level=0.05)` | `True` when `p_value >= significance_level`. |

`x` and `y` are column names or column indices. `z` is a list of column names or indices.

```{literalinclude} ../../crates/ci-python/examples/pearson_correlation.py
:language: python
:caption: crates/ci-python/examples/pearson_correlation.py
```

:::

:::{tab-item} R
:sync: r

`pearson_correlation(data)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `data` | `fastcit_dataset` from `dataset()`, or a `data.frame` | Required | The data. X, Y and the columns in Z must be continuous. Double columns are continuous. |

| Function | Returns |
|---|---|
| `run_test(test, x, y, z = character())` | A list with `statistic` (the partial correlation r), `p_value`, `dof` (the degrees of freedom of the t-test) and `effect_size` (the absolute partial correlation). |
| `is_independent(test, x, y, z = character(), significance_level = 0.05)` | `TRUE` when `p_value >= significance_level`. |

`x` and `y` are column names. `z` is a character vector of column names.

```{literalinclude} ../../crates/ci-r/inst/examples/tests/pearson_correlation.R
:language: r
:caption: crates/ci-r/inst/examples/tests/pearson_correlation.R
```

:::

:::{tab-item} JavaScript
:sync: javascript

`new PearsonCorrelation(data)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `data` | `Dataset`, or an object `{ name: { kind, values } }` | Required | The data. X, Y and the columns in Z must have `kind: "continuous"`. |

The constructor accepts no options.

| Method | Returns |
|---|---|
| `runTest(x, y, z)` | An object `{ statistic, pValue, dof, effectSize }`. `statistic` is the partial correlation r. `dof` is the degrees of freedom of the t-test. `effectSize` is the absolute partial correlation. |
| `isIndependent(x, y, z, significanceLevel = 0.05)` | `true` when `pValue >= significanceLevel`. |

`x` and `y` are column names. `z` is an array of column names. Use `[]` for an empty Z.

```{literalinclude} ../../crates/ci-js/examples/pearson_correlation.js
:language: javascript
:caption: crates/ci-js/examples/pearson_correlation.js
```

:::

:::{tab-item} Rust
:sync: rust

`fastcit_core::ci_tests::PearsonCorrelation`

`PearsonCorrelation` has no fields. Make it with `PearsonCorrelation::new()` or `PearsonCorrelation::default()`.

| Method (trait `CITest`) | Returns |
|---|---|
| `test(&data, x, y, &z)` | `Result<CiResult, CiError>`. `CiResult` has `statistic` (the partial correlation r), `p_value`, `dof` (the degrees of freedom of the t-test) and `effect_size` (the absolute partial correlation). |
| `is_independent(&data, x, y, &z, alpha)` | `Result<bool, CiError>`: `true` when `p_value >= alpha`. |

`x` and `y` are column indices. `z` is a slice of column indices. Get an index with `data.index_of(name)`.

```{literalinclude} ../../crates/ci-core/examples/pearson_correlation.rs
:language: rust
:caption: crates/ci-core/examples/pearson_correlation.rs
```

:::
::::

## Method

**Partial correlation.**
FastCIT regresses X on $[1, Z]$ and Y on $[1, Z]$ with ordinary least squares.
The partial correlation $r$ is the Pearson correlation of the two residual vectors.
With an empty Z, $r$ is the Pearson correlation of X and Y.

When the data has at most 2048 continuous columns, FastCIT keeps a matrix of sums of products of these columns.
It makes this matrix in the first call and uses it to calculate $r$ in later calls.
For finite data, this method gives the same $r$ as the regression.

**Statistic.**
The statistic is $r$.
FastCIT reports $r$, not the $t$ value below.

**Degrees of freedom.**
With $n$ rows and $|Z|$ conditioning variables, the degrees of freedom are

$$
\mathrm{dof} = n - |Z| - 2.
$$

**p-value.**
FastCIT changes $r$ into a $t$ value:

$$
t = r \sqrt{\frac{\mathrm{dof}}{1 - r^2}}.
$$

Under independence, $t$ has Student's t-distribution with $\mathrm{dof}$ degrees of freedom when the data is Gaussian.
The p-value is two-sided:

$$
p = 2 \, P\left(T_{\mathrm{dof}} \geq |t|\right).
$$

`is_independent` returns true when the p-value is greater than or equal to the significance level.

**Effect size.**
The effect size is $|r|$.

**Limits and errors.**
The test needs at least $|Z| + 3$ rows, so the degrees of freedom are at least 1.
The test returns an error when $|r| = 1$, because $t$ then has no value.
It also returns an error when X or Y is constant.
It returns an error when Z explains X or Y almost completely, or when the columns of Z are linearly dependent.
The test returns an error when X, Y or a column in Z is discrete.

## References

- Pearson, K. (1896). Mathematical contributions to the theory of evolution. III. Regression, heredity, and panmixia. *Philosophical Transactions of the Royal Society of London, Series A*, 187, 253–318. <https://doi.org/10.1098/rsta.1896.0007>
- Fisher, R. A. (1915). Frequency distribution of the values of the correlation coefficient in samples from an indefinitely large population. *Biometrika*, 10(4), 507–521. <https://doi.org/10.2307/2331838>
- Fisher, R. A. (1924). The distribution of the partial correlation coefficient. *Metron*, 3, 329–332.
