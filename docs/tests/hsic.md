---
myst:
  html_meta:
    description: The HSIC kernel independence test in FastCIT, with examples for Python, R, JavaScript and Rust.
---

# HSIC test

:Data types: X and Y must be continuous. HSIC has no Z.

## Usage

::::{tab-set}
:sync-group: language

:::{tab-item} Python
:sync: python

`fastcit.HSIC(data, kernel=None, bandwidth="heuristic", null_dist="gamma", n_permutations=100, seed=0)`

```{literalinclude} ../../crates/ci-python/examples/hsic.py
:language: python
```

:::

:::{tab-item} R
:sync: r

`hsic(data, kernel = NULL, bandwidth = "heuristic", null_dist = "gamma", n_permutations = 100L, seed = 0)`

```{literalinclude} ../../crates/ci-r/inst/examples/tests/hsic.R
:language: r
```

:::

:::{tab-item} JavaScript
:sync: javascript

`new HSIC(data, { kernel: undefined, kernels: undefined, bandwidth: "heuristic", nullDist: "gamma", nPermutations: 100, seed: 0 })`

```{literalinclude} ../../crates/ci-js/examples/hsic.js
:language: javascript
```

:::

:::{tab-item} Rust
:sync: rust

`fastcit_core::ci_tests::Hsic { kernel: KernelChoice::Auto, bandwidth: Bandwidth::Heuristic, null_dist: NullDistribution::Gamma }`

```{literalinclude} ../../crates/ci-core/examples/hsic.rs
:language: rust
```

:::
::::

## Method

FastCIT standardises X and Y with the sample standard deviation, which divides by $n - 1$.
$K$ and $L$ are the $n \times n$ kernel matrices of X and Y.
The default kernel is the RBF kernel, with length scale $\ell$.

$$
\begin{aligned}
k_{\mathrm{RBF}}(a, b) &= \exp\left(-\frac{(a - b)^2}{2 \ell^2}\right), \\
k_{\mathrm{linear}}(a, b) &= a \, b.
\end{aligned}
$$

With `bandwidth = "heuristic"`, $\ell$ is 0.8 for $n < 200$, 0.5 for $200 \leq n < 1200$ and 0.3 for $n \geq 1200$.
With `"median"`, $\ell$ is the median of the non-zero distances between pairs of rows, divided by $\sqrt{2}$.
$H = I - \frac{1}{n} \mathbf{1} \mathbf{1}^\top$ is the centring matrix, $\tilde K = H K H$ and $\tilde L = H L H$.

$$
T = \sum_{i,j} \tilde K_{ij} \, \tilde L_{ij} = \operatorname{tr}\left(\tilde K \tilde L\right).
$$

FastCIT does not divide $T$ by $n^2$.
With `null_dist = "gamma"`, $\mu_K$ is the mean of $K_{ij}$ for $i \neq j$, and $\mu_L$ is the same for $L$.

$$
\begin{aligned}
\mathbb{E} &= \frac{1}{n} \left( \frac{\operatorname{tr} K}{n} - \mu_K \right) \left( \frac{\operatorname{tr} L}{n} - \mu_L \right), \\
\mathbb{V} &= \frac{72 \, (n - 4)(n - 5)}{n (n - 1)(n - 2)(n - 3)} \cdot \frac{1}{n (n - 1)} \sum_{i \neq j} \left( \frac{\tilde K_{ij} \, \tilde L_{ij}}{6} \right)^2.
\end{aligned}
$$

The p-value is the upper tail at $T / n$ of a gamma distribution.
Its shape is $\mathbb{E}^2 / \mathbb{V}$ and its scale is $n \, \mathbb{V} / \mathbb{E}$.
With `null_dist = "permutation"`, $B$ random permutations $\pi_b$ of the rows give

$$
T_b = \sum_{i,j} \tilde K_{ij} \, \tilde L_{\pi_b(i) \pi_b(j)}, \qquad
p = \frac{1 + \#\{b : T_b \geq T\}}{1 + B}.
$$

$B$ is `n_permutations`.
The effect size is $T / \sqrt{\operatorname{tr}\left(\tilde K \tilde K\right) \operatorname{tr}\left(\tilde L \tilde L\right)}$.
