---
myst:
  html_meta:
    description: The KCI kernel conditional independence test in FastCIT, with examples for Python, R, JavaScript and Rust.
---

# KCI test

:Data types: X, Y and Z must be continuous.

## Usage

::::{tab-set}
:sync-group: language

:::{tab-item} Python
:sync: python

`fastcit.KCI(data, kernel=None, bandwidth="heuristic", epsilon=1e-3)`

```{literalinclude} ../../crates/ci-python/examples/kci.py
:language: python
```

:::

:::{tab-item} R
:sync: r

`kci(data, kernel = NULL, bandwidth = "heuristic", epsilon = 1e-3)`

```{literalinclude} ../../crates/ci-r/inst/examples/tests/kci.R
:language: r
```

:::

:::{tab-item} JavaScript
:sync: javascript

`new KCI(data, { kernel: undefined, kernels: undefined, bandwidth: "heuristic", epsilon: 0.001 })`

```{literalinclude} ../../crates/ci-js/examples/kci.js
:language: javascript
```

:::

:::{tab-item} Rust
:sync: rust

`fastcit_core::ci_tests::Kci { kernel: KernelChoice::Auto, bandwidth: Bandwidth::Heuristic, epsilon: 1e-3 }`

```{literalinclude} ../../crates/ci-core/examples/kci.rs
:language: rust
```

:::
::::

## Method

With an empty Z, KCI runs the {doc}`hsic` with the gamma null.
Otherwise, FastCIT standardises X, Y and Z with the sample standard deviation, which divides by $n - 1$.
The kernel of X uses $\ddot X = (X, Z/2)$.
The kernel of Y uses Y, and the kernel of Z uses Z.
The default kernel is the RBF kernel $k(a, b) = \exp\left(-\lVert a - b \rVert^2 / (2 \ell^2)\right)$.
With `bandwidth = "heuristic"`, $\ell = w \sqrt{|Z|}$ for all three kernels.
$w$ is 1.2 for $n < 200$, 0.7 for $200 \leq n < 1200$ and 0.4 for $n \geq 1200$.
With `"median"`, $\ell$ is the median of the non-zero distances between pairs of rows, divided by $\sqrt{2}$.

$\tilde K = H K H$ is a centred kernel matrix, with $H = I - \frac{1}{n} \mathbf{1} \mathbf{1}^\top$.
$\varepsilon$ is `epsilon`.

$$
\begin{aligned}
R_Z &= \varepsilon \left( \tilde K_Z + \varepsilon I \right)^{-1}, \\
\tilde K_{\ddot X \mid Z} &= R_Z \, \tilde K_{\ddot X} \, R_Z, \\
\tilde K_{Y \mid Z} &= R_Z \, \tilde K_Y \, R_Z, \\
T &= \operatorname{tr}\left( \tilde K_{\ddot X \mid Z} \, \tilde K_{Y \mid Z} \right).
\end{aligned}
$$

$V_X$ has the columns $\sqrt{\lambda} \, u$ for the eigenpairs of $\tilde K_{\ddot X \mid Z}$ with $\lambda > 10^{-5} \lambda_{\max}$.
$V_Y$ is the same for $\tilde K_{Y \mid Z}$.

$$
\begin{aligned}
W &= \left( V_X V_X^\top \right) \circ \left( V_Y V_Y^\top \right), \\
\text{mean} &= \operatorname{tr} W, \\
\text{variance} &= 2 \operatorname{tr}\left( W^2 \right).
\end{aligned}
$$

The p-value is the upper tail at $T$ of a gamma distribution.
Its shape is $\text{mean}^2 / \text{variance}$ and its scale is $\text{variance} / \text{mean}$.
The effect size is $T / \sqrt{\operatorname{tr}\left( \tilde K_{\ddot X \mid Z}^2 \right) \operatorname{tr}\left( \tilde K_{Y \mid Z}^2 \right)}$.
