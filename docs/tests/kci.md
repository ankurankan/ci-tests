---
myst:
  html_meta:
    description: The KCI kernel conditional independence test in FastCIT, with parameters and examples for Python, R, JavaScript and Rust.
---

# KCI test

:Data type: Continuous
:Python and JavaScript: `KCI`
:R: `kci()`
:Rust: `fastcit_core::ci_tests::Kci`

The kernel-based conditional independence (KCI) test checks whether two continuous variables X and Y are independent given a set Z of continuous variables.
It uses kernel matrices, so it also finds nonlinear dependence and nonlinear effects of Z.

## When to use

- X, Y and all the variables in Z are continuous.
- The relations between the variables can be nonlinear. For linear relations, {doc}`fisher_z` is much faster.
- The number of rows is moderate. The test keeps $n \times n$ matrices, and its time grows with $n^3$.
- KCI is not symmetric. The tests of X and Y given Z and of Y and X given Z can give different p-values.
- Without Z, KCI is the same as the {doc}`hsic` with the gamma null.

## Usage and parameters

Select your language.
Each tab shows the constructor, its parameters and an example.
The CI of each language runs the example file.

::::{tab-set}
:sync-group: language

:::{tab-item} Python
:sync: python

`fastcit.KCI(data, kernel=None, bandwidth="heuristic", epsilon=1e-3)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `data` | `fastcit.Dataset`, `dict` or `pandas.DataFrame` | Required | The data. X, Y and the columns in Z must be continuous. Other columns can have any kind. A `DataFrame` gives floating-point columns the continuous kind. |
| `kernel` | `None`, `fastcit.RBF`, `fastcit.Linear`, or a `dict` of them | `None` | `None` gives X, Y and Z RBF kernels with the `bandwidth` rule. One kernel applies to X, Y and Z. A `dict` gives the kernels of X and Y by column name. Z then gets the default kernel. |
| `bandwidth` | `str` | `"heuristic"` | The rule for the length scale of a default RBF kernel: `"heuristic"` or `"median"`. |
| `epsilon` | `float` | `1e-3` | The regularisation $\varepsilon$ that removes the effect of Z. It must be finite and greater than 0. |

Make a kernel with `fastcit.RBF(length_scale)` or `fastcit.Linear()`.
`length_scale` must be finite and greater than 0.

| Method | Returns |
|---|---|
| `run_test(x, y, z=None)` | A `CiResult` with `statistic` (the KCI statistic T), `p_value`, `dof` (`None`) and `effect_size` (the normalised statistic). |
| `is_independent(x, y, z=None, significance_level=0.05)` | `True` when `p_value >= significance_level`. |

`x` and `y` are column names or column indices. `z` is a list of column names or indices.

```{literalinclude} ../../crates/ci-python/examples/kci.py
:language: python
:caption: crates/ci-python/examples/kci.py
```

:::

:::{tab-item} R
:sync: r

`kci(data, kernel = NULL, bandwidth = "heuristic", epsilon = 1e-3)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `data` | `fastcit_dataset` from `dataset()`, or a `data.frame` | Required | The data. X, Y and the columns in Z must be continuous. Double columns are continuous. Other columns can have any kind. |
| `kernel` | `NULL`, a `fastcit_kernel`, or a named list of them | `NULL` | `NULL` gives X, Y and Z RBF kernels with the `bandwidth` rule. One kernel applies to X, Y and Z. A named list gives the kernels of X and Y by column name. Z then gets the default kernel. |
| `bandwidth` | `character` | `"heuristic"` | The rule for the length scale of a default RBF kernel: `"heuristic"` or `"median"`. |
| `epsilon` | `numeric` | `1e-3` | The regularisation $\varepsilon$ that removes the effect of Z. It must be finite and greater than 0. |

Make a kernel with `rbf_kernel(length_scale)` or `linear_kernel()`.
`length_scale` must be finite and greater than 0.

| Function | Returns |
|---|---|
| `run_test(test, x, y, z = character())` | A list with `statistic` (the KCI statistic T), `p_value`, `dof` (`NULL`) and `effect_size` (the normalised statistic). |
| `is_independent(test, x, y, z = character(), significance_level = 0.05)` | `TRUE` when `p_value >= significance_level`. |

`x` and `y` are column names. `z` is a character vector of column names.

```{literalinclude} ../../crates/ci-r/inst/examples/tests/kci.R
:language: r
:caption: crates/ci-r/inst/examples/tests/kci.R
```

:::

:::{tab-item} JavaScript
:sync: javascript

`new KCI(data, options)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `data` | `Dataset`, or an object `{ name: { kind, values } }` | Required | The data. X, Y and the columns in Z must have `kind: "continuous"`. Other columns can have any kind. |
| `options.kernel` | `{ type: "rbf", lengthScale }` or `{ type: "linear" }` | None | One kernel for X, Y and Z. Without `kernel` and `kernels`, X, Y and Z get RBF kernels with the `bandwidth` rule. |
| `options.kernels` | `Record<string, KernelSpec>` | None | The kernels of X and Y by column name. Z then gets the default kernel. Do not use it together with `kernel`. |
| `options.bandwidth` | `"heuristic"` or `"median"` | `"heuristic"` | The rule for the length scale of a default RBF kernel. |
| `options.epsilon` | `number` | `0.001` | The regularisation $\varepsilon$ that removes the effect of Z. It must be finite and greater than 0. |

`KernelSpec` is `{ type: "rbf", lengthScale }` or `{ type: "linear" }`.
`lengthScale` must be finite and greater than 0.
The constructor rejects an unknown option name.

| Method | Returns |
|---|---|
| `runTest(x, y, z)` | An object `{ statistic, pValue, dof, effectSize }`. `statistic` is the KCI statistic T. `dof` is `null`. `effectSize` is the normalised statistic. |
| `isIndependent(x, y, z, significanceLevel = 0.05)` | `true` when `pValue >= significanceLevel`. |

`x` and `y` are column names. `z` is an array of column names. Use `[]` for an empty Z.

```{literalinclude} ../../crates/ci-js/examples/kci.js
:language: javascript
:caption: crates/ci-js/examples/kci.js
```

:::

:::{tab-item} Rust
:sync: rust

`fastcit_core::ci_tests::Kci { kernel: KernelChoice, bandwidth: Bandwidth, epsilon: f64 }`

| Field | Type | `Kci::new()` | Description |
|---|---|---|---|
| `kernel` | `KernelChoice` | `KernelChoice::Auto` | `Auto` gives X, Y and Z the default RBF kernels. `All(kernel)` gives one kernel to X, Y and Z. `PerColumn(map)` gives the kernels of X and Y by column name. |
| `bandwidth` | `Bandwidth` | `Bandwidth::Heuristic` | The rule for the length scale of a default RBF kernel: `Heuristic` or `Median`. |
| `epsilon` | `f64` | `1e-3` | The regularisation $\varepsilon$ that removes the effect of Z. It must be finite and greater than 0. |

`Kernel`, `KernelChoice` and `Bandwidth` are in `fastcit_core::kernel`.
A kernel is `Kernel::Rbf { length_scale }` or `Kernel::Linear`.

| Method (trait `CITest`) | Returns |
|---|---|
| `test(&data, x, y, &z)` | `Result<CiResult, CiError>`. `CiResult` has `statistic` (the KCI statistic T), `p_value`, `dof` (`None`) and `effect_size` (the normalised statistic). |
| `is_independent(&data, x, y, &z, alpha)` | `Result<bool, CiError>`: `true` when `p_value >= alpha`. |

`x` and `y` are column indices. `z` is a slice of column indices. Get an index with `data.index_of(name)`.

```{literalinclude} ../../crates/ci-core/examples/kci.rs
:language: rust
:caption: crates/ci-core/examples/kci.rs
```

:::
::::

## Method

**Empty Z.**
With an empty Z, FastCIT runs the {doc}`hsic` with the gamma null.
It uses the `kernel` and `bandwidth` options of KCI.
The `heuristic` rule then gives the length scales of the HSIC test.
The rest of this section is for a non-empty Z.

**Standardisation.**
FastCIT standardises X, Y and each column of Z.
It subtracts the mean and divides by the sample standard deviation, with $n - 1$ in the denominator.

**Kernel inputs.**
The kernel of X uses $\ddot X = (X, Z/2)$: X together with the standardised Z columns multiplied by 0.5.
The kernel of Y uses only Y, and the kernel of Z uses only Z.
Zhang et al. (2011) use $(X, Z)$ for the kernel of X. FastCIT uses $Z/2$, as pgmpy does.

**Kernels and bandwidth.**
A default kernel is an RBF kernel, $k(a, b) = \exp\left(-\lVert a - b \rVert^2 / (2 \ell^2)\right)$.
The `bandwidth` rule sets its length scale $\ell$:

- `heuristic`: $\ell = w \sqrt{|Z|}$ for all three kernels. $w = 1.2$ when $n < 200$, $w = 0.7$ when $200 \leq n < 1200$, and $w = 0.4$ when $n \geq 1200$.
- `median`: for each of $\ddot X$, Y and Z, $\ell$ is the median of the non-zero distances between pairs of rows, divided by $\sqrt{2}$. When all distances are 0, $\ell = 1$.

One kernel in `kernel` applies to $\ddot X$, Y and Z.
A kernel map sets the kernels of X and Y by column name, and the kernel of X then applies to $\ddot X$.
With a map, Z always gets the default kernel. A map entry for a column of Z has no effect.

**Removing the effect of Z.**
FastCIT centres the three kernel matrices: $\tilde K = H K H$, with $H = I - \frac{1}{n} \mathbf{1} \mathbf{1}^\top$.
Then it removes the part that Z explains:

$$
\begin{aligned}
R_Z &= \varepsilon \left( \tilde K_Z + \varepsilon I \right)^{-1}, \\
\tilde K_{\ddot X \mid Z} &= R_Z \, \tilde K_{\ddot X} \, R_Z, \\
\tilde K_{Y \mid Z} &= R_Z \, \tilde K_Y \, R_Z.
\end{aligned}
$$

$R_Z$ gives the residuals of a kernel ridge regression on Z, with the regularisation $\varepsilon$.

**Statistic.**
The statistic is

$$
T = \operatorname{tr}\left( \tilde K_{\ddot X \mid Z} \, \tilde K_{Y \mid Z} \right).
$$

**Null distribution.**
FastCIT calculates the eigenvalues $\lambda$ and the eigenvectors $u$ of $\tilde K_{\ddot X \mid Z}$, after it makes the matrix exactly symmetric.
It keeps each eigenvalue that is greater than $10^{-5}$ times the largest eigenvalue.
The columns of the matrix $V_X$ are $\sqrt{\lambda} \, u$ for the kept pairs.
FastCIT makes $V_Y$ from $\tilde K_{Y \mid Z}$ in the same way. Then

$$
W = \left( V_X V_X^\top \right) \circ \left( V_Y V_Y^\top \right),
$$

where $\circ$ is the element-wise product.
Under conditional independence, $T$ is approximately a weighted sum of $\chi^2_1$ variables, with the eigenvalues of $W$ as the weights.
FastCIT fits a gamma distribution with the same mean and variance:

$$
\text{mean} = \operatorname{tr} W,
\qquad
\text{variance} = 2 \operatorname{tr}\left( W^2 \right).
$$

The shape is $\text{mean}^2 / \text{variance}$ and the scale is $\text{variance} / \text{mean}$.
The p-value is the probability that this distribution is greater than or equal to $T$.
When the mean or the variance is not greater than 0, the p-value is 1.
The test has no degrees of freedom, so `dof` is empty.
`is_independent` returns true when the p-value is greater than or equal to the significance level.

**Effect size.**
The effect size is the normalised statistic:

$$
\frac{T}{\sqrt{\operatorname{tr}\left( \tilde K_{\ddot X \mid Z}^2 \right) \, \operatorname{tr}\left( \tilde K_{Y \mid Z}^2 \right)}}.
$$

When the denominator is 0, the effect size is 0.

**Asymmetry.**
Only the kernel of X contains Z.
So a swap of X and Y can change the statistic and the p-value.

**Cost.**
FastCIT keeps several $n \times n$ matrices in memory.
It inverts one matrix and calculates two eigendecompositions, so the time grows with $n^3$.

**Errors.**
The test returns an error when X, Y or a column in Z is discrete. Other discrete columns in the data are not a problem.
It also returns an error when X, Y or a column in Z is constant, or when the data has fewer than 2 rows.
An `epsilon` that is not finite and greater than 0 causes an error.
A length scale that is not finite and greater than 0 causes an error.
A kernel for a column name that is not in the data causes an error.
FastCIT checks `epsilon` and the kernels when you make the test. In Rust, it checks them when you run the test.
A failure of the matrix inversion or of an eigendecomposition causes a numeric error.
A missing value in the data causes an error.

## References

- Zhang, K., Peters, J., Janzing, D. and Schölkopf, B. (2011). Kernel-based conditional independence test and application in causal discovery. In *Proceedings of the 27th Conference on Uncertainty in Artificial Intelligence (UAI 2011)*, 804–813. <https://doi.org/10.48550/arXiv.1202.3775>
- Gretton, A., Fukumizu, K., Teo, C. H., Song, L., Schölkopf, B. and Smola, A. J. (2008). A kernel statistical test of independence. In *Advances in Neural Information Processing Systems 20 (NIPS 2007)*, 585–592. <https://proceedings.neurips.cc/paper/2007/hash/d5cfead94f5350c12c322b5b664544c1-Abstract.html>
- Cortes, C., Mohri, M. and Rostamizadeh, A. (2012). Algorithms for learning kernels based on centered alignment. *Journal of Machine Learning Research*, 13, 795–828. <https://jmlr.org/papers/v13/cortes12a.html>
