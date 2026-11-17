---
myst:
  html_meta:
    description: The HSIC kernel independence test in FastCIT, with parameters and examples for Python, R, JavaScript and Rust.
---

# HSIC test

:Data type: Continuous
:Python and JavaScript: `HSIC`
:R: `hsic()`
:Rust: `fastcit_core::ci_tests::Hsic`

The HSIC test checks whether two continuous variables X and Y are independent.
It has no conditioning set Z.
It compares kernel matrices of X and Y, so it also finds nonlinear dependence.

## When to use

- X and Y are continuous, and you do not condition on other variables. To condition on Z, use {doc}`kci`.
- The dependence can be nonlinear. For example, $Y = X^2 + \varepsilon$ has zero correlation, but HSIC finds the dependence.
- The number of rows is moderate. The test keeps $n \times n$ matrices, so memory and time grow at least with $n^2$.
- For linear dependence, {doc}`pearson_correlation` and {doc}`fisher_z` are faster.

## Usage and parameters

Select your language.
Each tab shows the constructor, its parameters and an example.
The CI of each language runs the example file.

::::{tab-set}
:sync-group: language

:::{tab-item} Python
:sync: python

`fastcit.HSIC(data, kernel=None, bandwidth="heuristic", null_dist="gamma", n_permutations=100, seed=0)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `data` | `fastcit.Dataset`, `dict` or `pandas.DataFrame` | Required | The data. X and Y must be continuous. Other columns can have any kind. A `DataFrame` gives floating-point columns the continuous kind. |
| `kernel` | `None`, `fastcit.RBF`, `fastcit.Linear`, or a `dict` of them | `None` | `None` gives X and Y an RBF kernel with the `bandwidth` rule. One kernel applies to X and Y. A `dict` gives kernels by column name, and a column without an entry gets the default kernel. |
| `bandwidth` | `str` | `"heuristic"` | The rule for the length scale of a default RBF kernel: `"heuristic"` or `"median"`. |
| `null_dist` | `str` | `"gamma"` | The null distribution: `"gamma"` or `"permutation"`. |
| `n_permutations` | `int` | `100` | The number of permutations for the permutation null. It must be at least 1, also with the gamma null. |
| `seed` | `int` | `0` | The seed of the permutation null. It must be 0 or more. |

Make a kernel with `fastcit.RBF(length_scale)` or `fastcit.Linear()`.
`length_scale` must be finite and greater than 0.

| Method | Returns |
|---|---|
| `run_test(x, y, z=None)` | A `CiResult` with `statistic` (the HSIC statistic T), `p_value`, `dof` (`None`) and `effect_size` (the normalised HSIC). |
| `is_independent(x, y, z=None, significance_level=0.05)` | `True` when `p_value >= significance_level`. |

`x` and `y` are column names or column indices. HSIC has no Z, so `z` must be `None` or empty.

```{literalinclude} ../../crates/ci-python/examples/hsic.py
:language: python
:caption: crates/ci-python/examples/hsic.py
```

:::

:::{tab-item} R
:sync: r

`hsic(data, kernel = NULL, bandwidth = "heuristic", null_dist = "gamma", n_permutations = 100L, seed = 0)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `data` | `fastcit_dataset` from `dataset()`, or a `data.frame` | Required | The data. X and Y must be continuous. Double columns are continuous. Other columns can have any kind. |
| `kernel` | `NULL`, a `fastcit_kernel`, or a named list of them | `NULL` | `NULL` gives X and Y an RBF kernel with the `bandwidth` rule. One kernel applies to X and Y. A named list gives kernels by column name, and a column without an entry gets the default kernel. |
| `bandwidth` | `character` | `"heuristic"` | The rule for the length scale of a default RBF kernel: `"heuristic"` or `"median"`. |
| `null_dist` | `character` | `"gamma"` | The null distribution: `"gamma"` or `"permutation"`. |
| `n_permutations` | `numeric` | `100L` | The number of permutations for the permutation null. It must be a whole number from 1 to $2^{53}$, also with the gamma null. |
| `seed` | `numeric` | `0` | The seed of the permutation null. It must be a whole number from 0 to $2^{53}$. |

Make a kernel with `rbf_kernel(length_scale)` or `linear_kernel()`.
`length_scale` must be finite and greater than 0.

| Function | Returns |
|---|---|
| `run_test(test, x, y, z = character())` | A list with `statistic` (the HSIC statistic T), `p_value`, `dof` (`NULL`) and `effect_size` (the normalised HSIC). |
| `is_independent(test, x, y, z = character(), significance_level = 0.05)` | `TRUE` when `p_value >= significance_level`. |

`x` and `y` are column names. HSIC has no Z, so `z` must be empty.

```{literalinclude} ../../crates/ci-r/inst/examples/tests/hsic.R
:language: r
:caption: crates/ci-r/inst/examples/tests/hsic.R
```

:::

:::{tab-item} JavaScript
:sync: javascript

`new HSIC(data, options)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `data` | `Dataset`, or an object `{ name: { kind, values } }` | Required | The data. X and Y must have `kind: "continuous"`. Other columns can have any kind. |
| `options.kernel` | `{ type: "rbf", lengthScale }` or `{ type: "linear" }` | None | One kernel for X and Y. Without `kernel` and `kernels`, X and Y get an RBF kernel with the `bandwidth` rule. |
| `options.kernels` | `Record<string, KernelSpec>` | None | Kernels by column name. A column without an entry gets the default kernel. Do not use it together with `kernel`. |
| `options.bandwidth` | `"heuristic"` or `"median"` | `"heuristic"` | The rule for the length scale of a default RBF kernel. |
| `options.nullDist` | `"gamma"` or `"permutation"` | `"gamma"` | The null distribution. |
| `options.nPermutations` | `number` | `100` | The number of permutations for the permutation null. It must be a safe integer of at least 1, also with the gamma null. |
| `options.seed` | `number` | `0` | The seed of the permutation null. It must be a safe integer of at least 0. |

`KernelSpec` is `{ type: "rbf", lengthScale }` or `{ type: "linear" }`.
`lengthScale` must be finite and greater than 0.
The constructor rejects an unknown option name.

| Method | Returns |
|---|---|
| `runTest(x, y, z)` | An object `{ statistic, pValue, dof, effectSize }`. `statistic` is the HSIC statistic T. `dof` is `null`. `effectSize` is the normalised HSIC. |
| `isIndependent(x, y, z, significanceLevel = 0.05)` | `true` when `pValue >= significanceLevel`. |

`x` and `y` are column names. HSIC has no Z, so `z` must be `[]`.

```{literalinclude} ../../crates/ci-js/examples/hsic.js
:language: javascript
:caption: crates/ci-js/examples/hsic.js
```

:::

:::{tab-item} Rust
:sync: rust

`fastcit_core::ci_tests::Hsic { kernel: KernelChoice, bandwidth: Bandwidth, null_dist: NullDistribution }`

| Field | Type | `Hsic::new()` | Description |
|---|---|---|---|
| `kernel` | `KernelChoice` | `KernelChoice::Auto` | `Auto` gives X and Y the default RBF kernel. `All(kernel)` gives one kernel to X and Y. `PerColumn(map)` gives kernels by column name. |
| `bandwidth` | `Bandwidth` | `Bandwidth::Heuristic` | The rule for the length scale of a default RBF kernel: `Heuristic` or `Median`. |
| `null_dist` | `NullDistribution` | `NullDistribution::Gamma` | `Gamma`, or `Permutation { n_permutations, seed }`. `n_permutations` must be at least 1. |

`Kernel`, `KernelChoice` and `Bandwidth` are in `fastcit_core::kernel`.
A kernel is `Kernel::Rbf { length_scale }` or `Kernel::Linear`.
`NullDistribution` is in `fastcit_core::ci_tests`.

| Method (trait `CITest`) | Returns |
|---|---|
| `test(&data, x, y, &[])` | `Result<CiResult, CiError>`. `CiResult` has `statistic` (the HSIC statistic T), `p_value`, `dof` (`None`) and `effect_size` (the normalised HSIC). |
| `is_independent(&data, x, y, &[], alpha)` | `Result<bool, CiError>`: `true` when `p_value >= alpha`. |

`x` and `y` are column indices. HSIC has no Z, so give an empty slice. Get an index with `data.index_of(name)`.

```{literalinclude} ../../crates/ci-core/examples/hsic.rs
:language: rust
:caption: crates/ci-core/examples/hsic.rs
```

:::
::::

## Method

**No conditioning set.**
HSIC tests only whether X and Y are independent.
A non-empty Z causes an error. To condition on Z, use {doc}`kci`.

**Standardisation.**
FastCIT standardises X and Y.
It subtracts the mean and divides by the sample standard deviation, with $n - 1$ in the denominator.

**Kernels.**
From the standardised values, FastCIT makes the $n \times n$ kernel matrix $K$ of X and $L$ of Y.
The two kernels are

$$
\begin{aligned}
k_{\mathrm{RBF}}(a, b) &= \exp\left(-\frac{(a - b)^2}{2 \ell^2}\right), \\
k_{\mathrm{linear}}(a, b) &= a \, b.
\end{aligned}
$$

**Bandwidth.**
The `bandwidth` rule sets the length scale $\ell$ of a default RBF kernel.
A kernel that you give keeps its own length scale.

- `heuristic`: $\ell = 0.8$ when $n < 200$, $\ell = 0.5$ when $200 \leq n < 1200$, and $\ell = 0.3$ when $n \geq 1200$.
- `median`: $\ell$ is the median of the non-zero distances between pairs of rows, divided by $\sqrt{2}$. FastCIT calculates it for X and for Y separately. When all distances are 0, $\ell = 1$.

**Statistic.**
With the centring matrix $H = I - \frac{1}{n} \mathbf{1} \mathbf{1}^\top$, the centred kernel matrices are $\tilde K = H K H$ and $\tilde L = H L H$.
The statistic is

$$
T = \sum_{i,j} \tilde K_{ij} \, \tilde L_{ij} = \operatorname{tr}\left(\tilde K \tilde L\right).
$$

FastCIT does not divide $T$ by $n^2$.
With linear kernels, $T = \left((n - 1) \, r\right)^2$, where $r$ is the Pearson correlation of X and Y.

**Gamma null.**
This is the default null distribution.
It follows Gretton et al. (2008).
With $\mu_K = \frac{1}{n(n - 1)} \sum_{i \neq j} K_{ij}$, and $\mu_L$ the same for $L$, FastCIT calculates

$$
\mathbb{E} = \frac{1}{n} \left( \frac{\operatorname{tr} K}{n} - \mu_K \right) \left( \frac{\operatorname{tr} L}{n} - \mu_L \right),
$$

$$
\begin{aligned}
\mathbb{V} &= \frac{72 \, (n - 4)(n - 5)}{n (n - 1)(n - 2)(n - 3)} \, S, \\
S &= \frac{1}{n (n - 1)} \sum_{i \neq j} \left( \frac{\tilde K_{ij} \, \tilde L_{ij}}{6} \right)^2.
\end{aligned}
$$

$\mathbb{E}$ and $\mathbb{V}$ estimate the mean and the variance of $T / n^2$ under independence.
FastCIT fits a gamma distribution with mean $n \, \mathbb{E}$ and variance $n^2 \, \mathbb{V}$.
Its shape is $\mathbb{E}^2 / \mathbb{V}$ and its scale is $n \, \mathbb{V} / \mathbb{E}$.
The p-value is the probability that this distribution is greater than or equal to $T / n$.
With fewer than 6 rows, the p-value is 1.
When $\mathbb{E} \leq 0$ or $\mathbb{V} \leq 0$, the p-value is also 1.

**Permutation null.**
With `null_dist` set to `"permutation"`, FastCIT makes $B$ random permutations $\pi_b$ of the rows, where $B$ is `n_permutations`:

$$
\begin{aligned}
T_b &= \sum_{i,j} \tilde K_{ij} \, \tilde L_{\pi_b(i) \pi_b(j)}, \\
p &= \frac{1 + \#\{b : T_b \geq T\}}{1 + B}.
\end{aligned}
$$

A SplitMix64 generator, started from `seed`, makes the permutations.
With the same data and seed, FastCIT makes the same permutations.
The smallest possible p-value is $1 / (B + 1)$.

**p-value and decision.**
The test has no degrees of freedom, so `dof` is empty.
`is_independent` returns true when the p-value is greater than or equal to the significance level.

**Effect size.**
The effect size is the normalised HSIC:

$$
\frac{T}{\sqrt{\operatorname{tr}\left(\tilde K \tilde K\right) \, \operatorname{tr}\left(\tilde L \tilde L\right)}}.
$$

This is the centred kernel alignment of Cortes et al. (2012).
With linear kernels, it is $r^2$.
When the denominator is 0, the effect size is 0.

**Errors.**
The test returns an error when Z is not empty.
It returns an error when X or Y is discrete. Other discrete columns in the data are not a problem.
It also returns an error when X or Y is constant, or when the data has fewer than 2 rows.
A length scale that is not finite and greater than 0 causes an error.
A kernel for a column name that is not in the data causes an error.
FastCIT checks the kernels and `n_permutations` when you make the test. In Rust, it checks them when you run the test.
A missing value in the data causes an error.

## References

- Gretton, A., Bousquet, O., Smola, A. and Schölkopf, B. (2005). Measuring statistical dependence with Hilbert-Schmidt norms. In *Algorithmic Learning Theory (ALT 2005)*, Lecture Notes in Computer Science 3734, 63–77. <https://doi.org/10.1007/11564089_7>
- Gretton, A., Fukumizu, K., Teo, C. H., Song, L., Schölkopf, B. and Smola, A. J. (2008). A kernel statistical test of independence. In *Advances in Neural Information Processing Systems 20 (NIPS 2007)*, 585–592. <https://proceedings.neurips.cc/paper/2007/hash/d5cfead94f5350c12c322b5b664544c1-Abstract.html>
- Cortes, C., Mohri, M. and Rostamizadeh, A. (2012). Algorithms for learning kernels based on centered alignment. *Journal of Machine Learning Research*, 13, 795–828. <https://jmlr.org/papers/v13/cortes12a.html>
