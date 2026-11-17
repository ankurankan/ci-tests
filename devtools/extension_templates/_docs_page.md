---
myst:
  html_meta:
    description: The <Title> conditional independence test in FastCIT, with examples for Python, R, JavaScript and Rust.
---

<!--
TEMPLATE: Copy this file to docs/tests/<key>.md. Resolve every TODO. Delete every comment like this one.
Names: <Title> is the display name. <PyClass> is the Python and JavaScript class. <key> is the R function and the file name.
<Class> is the Rust struct. Copy the layout of docs/tests/chi_squared.md.
Each language tab has the constructor line, then the example file. Show every option in the constructor line.
tests/test_docs_site.py checks the headings, the tab order and the constructor lines.
-->

# <Title> test

:Data types: TODO X, Y and Z must be continuous. (Or discrete. Or mixed.)
:API: The same for all tests. See [one API for all tests](../index.md#one-api-for-all-tests).

## Usage

::::{tab-set}
:sync-group: language

:::{tab-item} Python
:sync: python

`fastcit.<PyClass>(data)`

```{literalinclude} ../../crates/ci-python/examples/<key>.pycon
:language: pycon
```

:::

:::{tab-item} R
:sync: r

`<key>(data)`

```{literalinclude} ../../crates/ci-r/inst/examples/tests/<key>.R
:language: r
```

:::

:::{tab-item} JavaScript
:sync: javascript

`new <PyClass>(data)`

```{literalinclude} ../../crates/ci-js/examples/<key>.js
:language: javascript
```

:::

:::{tab-item} Rust
:sync: rust

`fastcit_core::ci_tests::<Class>`

```{literalinclude} ../../crates/ci-core/examples/<key>.rs
:language: rust
```

:::
::::

## Method

TODO Define every symbol in short sentences. Give the formulas only: no history, no advice.

$$
\begin{aligned}
T &= \text{TODO statistic}, \\
\mathrm{dof} &= \text{TODO degrees of freedom}, \\
p &= \text{TODO p-value}.
\end{aligned}
$$

TODO State the effect size. State how each option changes the formulas.
