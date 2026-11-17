---
myst:
  html_meta:
    description: The Pearson equivalence (TOST) conditional independence test in FastCIT, with parameters and examples for Python, R, JavaScript and Rust.
---

# Pearson equivalence test

:Data type: Continuous
:Python and JavaScript: `PearsonEquivalence`
:R: `pearson_equivalence()`
:Rust: `fastcit_core::ci_tests::PearsonEquivalence`

The Pearson equivalence test checks whether the partial correlation of two continuous variables X and Y given Z is negligible.
It uses two one-sided tests (TOST) to show that the partial correlation is between $-\delta$ and $\delta$.
A small p-value supports independence. This is the opposite of the other tests.

## When to use

- X, Y and all the variables in Z are continuous.
- The relations between the variables are approximately linear, and the noise is approximately Gaussian.
- You want evidence for independence. A standard test cannot give this evidence, because a large p-value can also come from a small sample.
- You can select a margin $\delta$. Select a value so that a partial correlation smaller than $\delta$ is not important for your work.
- In constraint-based causal discovery, the test removes an edge only when the data supports independence. Malinsky (2024) describes this approach.

## Usage and parameters

Select your language.
Each tab shows the constructor, its parameters and an example.
The CI of each language runs the example file.

::::{tab-set}
:sync-group: language

:::{tab-item} Python
:sync: python

`fastcit.PearsonEquivalence(data, delta_threshold=0.1)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `data` | `fastcit.Dataset`, `dict` or `pandas.DataFrame` | Required | The data. X, Y and the columns in Z must be continuous. A `DataFrame` gives floating-point columns the continuous kind. |
| `delta_threshold` | `float` | `0.1` | The equivalence margin $\delta$ on the correlation scale. It must be greater than 0 and less than 1. |

| Method | Returns |
|---|---|
| `run_test(x, y, z=None)` | A `CiResult` with `statistic` ($\operatorname{atanh}$ of the partial correlation), `p_value`, `dof` (`None`) and `effect_size` (the absolute partial correlation). |
| `is_independent(x, y, z=None, significance_level=0.05)` | `True` when `p_value < significance_level`. |

`x` and `y` are column names or column indices. `z` is a list of column names or indices.

```{literalinclude} ../../crates/ci-python/examples/pearson_equivalence.py
:language: python
:caption: crates/ci-python/examples/pearson_equivalence.py
```

:::

:::{tab-item} R
:sync: r

`pearson_equivalence(data, delta_threshold = 0.1)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `data` | `fastcit_dataset` from `dataset()`, or a `data.frame` | Required | The data. X, Y and the columns in Z must be continuous. Double columns are continuous. |
| `delta_threshold` | `numeric` | `0.1` | The equivalence margin $\delta$ on the correlation scale. It must be greater than 0 and less than 1. |

| Function | Returns |
|---|---|
| `run_test(test, x, y, z = character())` | A list with `statistic` ($\operatorname{atanh}$ of the partial correlation), `p_value`, `dof` (`NULL`) and `effect_size` (the absolute partial correlation). |
| `is_independent(test, x, y, z = character(), significance_level = 0.05)` | `TRUE` when `p_value < significance_level`. |

`x` and `y` are column names. `z` is a character vector of column names.

```{literalinclude} ../../crates/ci-r/inst/examples/tests/pearson_equivalence.R
:language: r
:caption: crates/ci-r/inst/examples/tests/pearson_equivalence.R
```

:::

:::{tab-item} JavaScript
:sync: javascript

`new PearsonEquivalence(data, options)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `data` | `Dataset`, or an object `{ name: { kind, values } }` | Required | The data. X, Y and the columns in Z must have `kind: "continuous"`. |
| `options.deltaThreshold` | `number` | `0.1` | The equivalence margin $\delta$ on the correlation scale. It must be greater than 0 and less than 1. |

| Method | Returns |
|---|---|
| `runTest(x, y, z)` | An object `{ statistic, pValue, dof, effectSize }`. `statistic` is $\operatorname{atanh}$ of the partial correlation. `dof` is `null`. `effectSize` is the absolute partial correlation. |
| `isIndependent(x, y, z, significanceLevel = 0.05)` | `true` when `pValue < significanceLevel`. |

`x` and `y` are column names. `z` is an array of column names. Use `[]` for an empty Z.

```{literalinclude} ../../crates/ci-js/examples/pearson_equivalence.js
:language: javascript
:caption: crates/ci-js/examples/pearson_equivalence.js
```

:::

:::{tab-item} Rust
:sync: rust

`fastcit_core::ci_tests::PearsonEquivalence { delta_threshold: f64 }`

| Field | Type | Default | Description |
|---|---|---|---|
| `delta_threshold` | `f64` | None. Give it to `PearsonEquivalence::new(delta_threshold)`. | The equivalence margin $\delta$ on the correlation scale. It must be greater than 0 and less than 1. `registry::make_default` uses `0.1`. |

| Method (trait `CITest`) | Returns |
|---|---|
| `test(&data, x, y, &z)` | `Result<CiResult, CiError>`. `CiResult` has `statistic` ($\operatorname{atanh}$ of the partial correlation), `p_value`, `dof` (`None`) and `effect_size` (the absolute partial correlation). |
| `is_independent(&data, x, y, &z, alpha)` | `Result<bool, CiError>`: `true` when `p_value < alpha`. |

`x` and `y` are column indices. `z` is a slice of column indices. Get an index with `data.index_of(name)`.

```{literalinclude} ../../crates/ci-core/examples/pearson_equivalence.rs
:language: rust
:caption: crates/ci-core/examples/pearson_equivalence.rs
```

:::
::::

## Method

**Partial correlation.**
FastCIT regresses X on $[1, Z]$ and Y on $[1, Z]$ with ordinary least squares.
The partial correlation $r$ is the Pearson correlation of the two residual vectors.
With an empty Z, $r$ is the Pearson correlation of X and Y.
FastCIT uses the same calculation as the {doc}`fisher_z`, including its matrix of sums of products.

**Hypotheses.**
With $\rho$ the partial correlation in the population, the test checks

$$
H_0: |\rho| \geq \delta
\qquad \text{against} \qquad
H_1: |\rho| < \delta.
$$

**Statistic.**
With $n$ rows and $|Z|$ conditioning variables, FastCIT calculates

$$
\begin{aligned}
\tilde r &= \operatorname{clip}\left(r, -1 + 10^{-6}, 1 - 10^{-6}\right), \\
z_r &= \operatorname{atanh}\left(\tilde r\right), \\
z_\delta &= \operatorname{atanh}(\delta), \\
c &= \sqrt{n - |Z| - 3}.
\end{aligned}
$$

The statistic is $z_r$. FastCIT does not multiply it by $c$.

**p-value.**
The test makes two one-sided tests:

$$
\begin{aligned}
p_{\mathrm{lower}} &= 1 - \Phi\left(c \, (z_r + z_\delta)\right), \\
p_{\mathrm{upper}} &= \Phi\left(c \, (z_r - z_\delta)\right),
\end{aligned}
$$

where $\Phi$ is the standard normal distribution function.
A small $p_{\mathrm{lower}}$ rejects $\rho \leq -\delta$.
A small $p_{\mathrm{upper}}$ rejects $\rho \geq \delta$.
The p-value is the larger of the two: $p = \max\left(p_{\mathrm{lower}}, p_{\mathrm{upper}}\right)$.
The test has no degrees of freedom, so `dof` is empty.

**Decision.**
`is_independent` returns true when the p-value is less than the significance level.
This rule is the opposite of the rule of the other tests.

**Effect size.**
The effect size is $|r|$, before the clip.

**Limits and errors.**
The test needs at least $|Z| + 3$ rows.
With exactly $|Z| + 3$ rows, $c = 0$ and the p-value is 0.5.
The test returns an error when `delta_threshold` is not between 0 and 1.
It checks the margin when you run the test, not when you make it.
The test returns an error when X or Y is constant.
It also returns an error when Z explains X or Y almost completely, or when the columns of Z are linearly dependent.
The test returns an error when X, Y or a column in Z is discrete.

## References

- Schuirmann, D. J. (1987). A comparison of the two one-sided tests procedure and the power approach for assessing the equivalence of average bioavailability. *Journal of Pharmacokinetics and Biopharmaceutics*, 15(6), 657–680. <https://doi.org/10.1007/BF01068419>
- Fisher, R. A. (1921). On the "probable error" of a coefficient of correlation deduced from a small sample. *Metron*, 1, 3–32.
- Malinsky, D. (2024). A cautious approach to constraint-based causal model selection. arXiv:2404.18232. <https://doi.org/10.48550/arXiv.2404.18232>
