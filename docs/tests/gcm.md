---
myst:
  html_meta:
    description: The generalised covariance measure (GCM) conditional independence test in FastCIT, with parameters and examples for Python, R, JavaScript and Rust.
---

# GCM test

:Data type: Continuous
:Python and JavaScript: `GCM`
:R: `gcm()`
:Rust: `fastcit_core::ci_tests::Gcm`

The generalised covariance measure (GCM) test checks whether two continuous variables X and Y are independent given a set Z of continuous variables.
It regresses X and Y on Z and tests whether the products of the residuals have a mean of zero.

## When to use

- X, Y and all the variables in Z are continuous. For discrete variables in Z, use {doc}`pillai`.
- The effect of Z on X and on Y is approximately linear. FastCIT uses linear regression, and it has no option for other regression methods.
- The noise does not have to be Gaussian. The test divides by the observed spread of the residual products.
- The test finds only a linear relation between the residuals. For nonlinear dependence, use {doc}`kci`.

## Usage and parameters

Select your language.
Each tab shows the constructor, its parameters and an example.
The CI of each language runs the example file.

::::{tab-set}
:sync-group: language

:::{tab-item} Python
:sync: python

`fastcit.GCM(data)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `data` | `fastcit.Dataset`, `dict` or `pandas.DataFrame` | Required | The data. X, Y and the columns in Z must be continuous. A `DataFrame` gives floating-point columns the continuous kind. |

| Method | Returns |
|---|---|
| `run_test(x, y, z=None)` | A `CiResult` with `statistic` (T), `p_value`, `dof` (`None`) and `effect_size` (the absolute correlation of the residuals). |
| `is_independent(x, y, z=None, significance_level=0.05)` | `True` when `p_value >= significance_level`. |

`x` and `y` are column names or column indices. `z` is a list of column names or indices.

```{literalinclude} ../../crates/ci-python/examples/gcm.py
:language: python
:caption: crates/ci-python/examples/gcm.py
```

:::

:::{tab-item} R
:sync: r

`gcm(data)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `data` | `fastcit_dataset` from `dataset()`, or a `data.frame` | Required | The data. X, Y and the columns in Z must be continuous. Double columns are continuous. |

| Function | Returns |
|---|---|
| `run_test(test, x, y, z = character())` | A list with `statistic` (T), `p_value`, `dof` (`NULL`) and `effect_size` (the absolute correlation of the residuals). |
| `is_independent(test, x, y, z = character(), significance_level = 0.05)` | `TRUE` when `p_value >= significance_level`. |

`x` and `y` are column names. `z` is a character vector of column names.

```{literalinclude} ../../crates/ci-r/inst/examples/tests/gcm.R
:language: r
:caption: crates/ci-r/inst/examples/tests/gcm.R
```

:::

:::{tab-item} JavaScript
:sync: javascript

`new GCM(data)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `data` | `Dataset`, or an object `{ name: { kind, values } }` | Required | The data. X, Y and the columns in Z must have `kind: "continuous"`. |

The constructor accepts no options.

| Method | Returns |
|---|---|
| `runTest(x, y, z)` | An object `{ statistic, pValue, dof, effectSize }`. `statistic` is T. `dof` is `null`. `effectSize` is the absolute correlation of the residuals. |
| `isIndependent(x, y, z, significanceLevel = 0.05)` | `true` when `pValue >= significanceLevel`. |

`x` and `y` are column names. `z` is an array of column names. Use `[]` for an empty Z.

```{literalinclude} ../../crates/ci-js/examples/gcm.js
:language: javascript
:caption: crates/ci-js/examples/gcm.js
```

:::

:::{tab-item} Rust
:sync: rust

`fastcit_core::ci_tests::Gcm`

`Gcm` has no fields. Make it with `Gcm::new()` or `Gcm::default()`.

| Method (trait `CITest`) | Returns |
|---|---|
| `test(&data, x, y, &z)` | `Result<CiResult, CiError>`. `CiResult` has `statistic` (T), `p_value`, `dof` (`None`) and `effect_size` (the absolute correlation of the residuals). |
| `is_independent(&data, x, y, &z, alpha)` | `Result<bool, CiError>`: `true` when `p_value >= alpha`. |

`x` and `y` are column indices. `z` is a slice of column indices. Get an index with `data.index_of(name)`.

```{literalinclude} ../../crates/ci-core/examples/gcm.rs
:language: rust
:caption: crates/ci-core/examples/gcm.rs
```

:::
::::

## Method

**Residuals.**
FastCIT regresses X on $[1, Z]$ and Y on $[1, Z]$ with ordinary least squares.
It uses a Householder QR decomposition of $[1, Z]$.
The residuals are $r_X$ and $r_Y$.
With an empty Z, the residuals are X and Y minus their means.
Shah and Peters (2020) allow any regression method. FastCIT uses only linear regression.

**Statistic.**
With $n$ rows and the residual products $R_i = r_{X,i} \, r_{Y,i}$, the statistic is

$$
T = \frac{\sum_{i} R_i}{\sqrt{n} \, \hat\sigma_R},
\qquad
\hat\sigma_R = \sqrt{\frac{1}{n} \sum_{i} \left( R_i - \bar R \right)^2}.
$$

$\hat\sigma_R$ divides by $n$, not by $n - 1$.

**p-value.**
Under conditional independence, and when the regressions are correct, $T$ has approximately a standard normal distribution.
The p-value is two-sided:

$$
p = 2 \left( 1 - \Phi\left( |T| \right) \right),
$$

where $\Phi$ is the standard normal distribution function.
The test has no degrees of freedom, so `dof` is empty.
`is_independent` returns true when the p-value is greater than or equal to the significance level.

**Effect size.**
The effect size is the absolute Pearson correlation of $r_X$ and $r_Y$.
This is the absolute partial correlation of X and Y given Z.

**Limits and errors.**
The test needs more rows than $[1, Z]$ has columns, so $n > |Z| + 1$.
It returns an error when X or Y is constant.
It returns an error when the columns of $[1, Z]$ are linearly dependent, for example a constant column or two Z columns with the same values.
FastCIT compares each pivot of the QR decomposition with the norm of its column. So the scale of a Z column does not change this decision.
The test returns an error when Z explains X or Y almost completely, so that a residual has no variance.
It also returns an error when all residual products are equal, so that $\hat\sigma_R = 0$.
The test returns an error when X, Y or a column in Z is discrete.
A missing value in the data causes an error.

## References

- Shah, R. D. and Peters, J. (2020). The hardness of conditional independence testing and the generalised covariance measure. *The Annals of Statistics*, 48(3), 1514–1538. <https://doi.org/10.1214/19-AOS1857>
