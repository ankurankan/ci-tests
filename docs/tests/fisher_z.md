---
myst:
  html_meta:
    description: The Fisher-z conditional independence test in FastCIT, with parameters and examples for Python, R, JavaScript and Rust.
---

# Fisher-z test

:Data type: Continuous
:Python and JavaScript: `FisherZ`
:R: `fisher_z()`
:Rust: `fastcit_core::ci_tests::FisherZ`

The Fisher-z test checks whether two continuous variables X and Y are independent given a set Z of continuous variables.
It applies Fisher's z-transform to the partial correlation of X and Y given Z.

## When to use

- X, Y and all the variables in Z are continuous.
- The relations between the variables are approximately linear, and the noise is approximately Gaussian.
- You run a constraint-based search, for example the PC algorithm, on Gaussian data. Many causal discovery packages use this test as their default for continuous data.
- The test finds only linear dependence. For nonlinear dependence, use {doc}`kci` or, without Z, {doc}`hsic`.
- {doc}`pearson_correlation` tests the same partial correlation with a t-test.

## Usage and parameters

Select your language.
Each tab shows the constructor, its parameters and an example.
The CI of each language runs the example file.

::::{tab-set}
:sync-group: language

:::{tab-item} Python
:sync: python

`fastcit.FisherZ(data)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `data` | `fastcit.Dataset`, `dict` or `pandas.DataFrame` | Required | The data. X, Y and the columns in Z must be continuous. A `DataFrame` gives floating-point columns the continuous kind. |

| Method | Returns |
|---|---|
| `run_test(x, y, z=None)` | A `CiResult` with `statistic` (z), `p_value`, `dof` (`None`) and `effect_size` (the absolute partial correlation). |
| `is_independent(x, y, z=None, significance_level=0.05)` | `True` when `p_value >= significance_level`. |

`x` and `y` are column names or column indices. `z` is a list of column names or indices.

```{literalinclude} ../../crates/ci-python/examples/fisher_z.py
:language: python
:caption: crates/ci-python/examples/fisher_z.py
```

:::

:::{tab-item} R
:sync: r

`fisher_z(data)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `data` | `fastcit_dataset` from `dataset()`, or a `data.frame` | Required | The data. X, Y and the columns in Z must be continuous. Double columns are continuous. |

| Function | Returns |
|---|---|
| `run_test(test, x, y, z = character())` | A list with `statistic` (z), `p_value`, `dof` (`NULL`) and `effect_size` (the absolute partial correlation). |
| `is_independent(test, x, y, z = character(), significance_level = 0.05)` | `TRUE` when `p_value >= significance_level`. |

`x` and `y` are column names. `z` is a character vector of column names.

```{literalinclude} ../../crates/ci-r/inst/examples/tests/fisher_z.R
:language: r
:caption: crates/ci-r/inst/examples/tests/fisher_z.R
```

:::

:::{tab-item} JavaScript
:sync: javascript

`new FisherZ(data)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `data` | `Dataset`, or an object `{ name: { kind, values } }` | Required | The data. X, Y and the columns in Z must have `kind: "continuous"`. |

The constructor accepts no options.

| Method | Returns |
|---|---|
| `runTest(x, y, z)` | An object `{ statistic, pValue, dof, effectSize }`. `dof` is `null`. `effectSize` is the absolute partial correlation. |
| `isIndependent(x, y, z, significanceLevel = 0.05)` | `true` when `pValue >= significanceLevel`. |

`x` and `y` are column names. `z` is an array of column names. Use `[]` for an empty Z.

```{literalinclude} ../../crates/ci-js/examples/fisher_z.js
:language: javascript
:caption: crates/ci-js/examples/fisher_z.js
```

:::

:::{tab-item} Rust
:sync: rust

`fastcit_core::ci_tests::FisherZ`

`FisherZ` has no fields. Make it with `FisherZ::new()` or `FisherZ::default()`.

| Method (trait `CITest`) | Returns |
|---|---|
| `test(&data, x, y, &z)` | `Result<CiResult, CiError>`. `CiResult` has `statistic` (z), `p_value`, `dof` (`None`) and `effect_size` (the absolute partial correlation). |
| `is_independent(&data, x, y, &z, alpha)` | `Result<bool, CiError>`: `true` when `p_value >= alpha`. |

`x` and `y` are column indices. `z` is a slice of column indices. Get an index with `data.index_of(name)`.

```{literalinclude} ../../crates/ci-core/examples/fisher_z.rs
:language: rust
:caption: crates/ci-core/examples/fisher_z.rs
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
With $n$ rows and $|Z|$ conditioning variables, the statistic is

$$
\begin{aligned}
z &= \sqrt{n - |Z| - 3}\; \operatorname{atanh}\left(\tilde r\right), \\
\tilde r &= \operatorname{clip}\left(r, -1 + 10^{-6}, 1 - 10^{-6}\right).
\end{aligned}
$$

The clip keeps the statistic finite when $|r| = 1$.

**p-value.**
Under independence, $z$ has approximately a standard normal distribution.
The p-value is two-sided:

$$
p = 2 \left(1 - \Phi\left(|z|\right)\right),
$$

where $\Phi$ is the standard normal distribution function.
The test has no degrees of freedom, so `dof` is empty.
`is_independent` returns true when the p-value is greater than or equal to the significance level.

**Effect size.**
The effect size is $|r|$, before the clip.

**Limits and errors.**
The test needs at least $|Z| + 3$ rows.
With exactly $|Z| + 3$ rows, the statistic is 0 and the p-value is 1.
The test returns an error when X or Y is constant.
It also returns an error when Z explains X or Y almost completely, or when the columns of Z are linearly dependent.
The test returns an error when X, Y or a column in Z is discrete.

## References

- Fisher, R. A. (1915). Frequency distribution of the values of the correlation coefficient in samples from an indefinitely large population. *Biometrika*, 10(4), 507–521. <https://doi.org/10.2307/2331838>
- Fisher, R. A. (1924). The distribution of the partial correlation coefficient. *Metron*, 3, 329–332.
- Kalisch, M. and Bühlmann, P. (2007). Estimating high-dimensional directed acyclic graphs with the PC-algorithm. *Journal of Machine Learning Research*, 8, 613–636. <https://jmlr.org/papers/v8/kalisch07a.html>
