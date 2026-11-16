# fastcit-core

`fastcit-core` is the dependency-light Rust implementation of data-bound
conditional-independence testing.

## API

Build a [`Dataset`](src/dataset.rs) from named discrete or continuous columns,
then pass it to a stateless test implementing [`CITest`](src/strategy.rs):
`test(&data, x, y, z)` returns the test result, while
`is_independent(&data, x, y, z, alpha)` returns an independence decision.

The twelve implementations are `ChiSquared`, `LogLikelihood`, `CressieRead`,
`FreemanTukey`, `ModifiedLikelihood`, `PearsonCorrelation`, `FisherZ`,
`PearsonEquivalence`, `Hsic`, `Kci`, `Gcm`, and `Pillai`.

`Hsic` and `Kci` are kernel tests (RBF and linear kernels, configured through
`KernelChoice` and `Bandwidth`). `Hsic` is unconditional; `Kci` conditions on
`z` at O(n²) memory and O(n³) time.

`Gcm` (continuous) and `Pillai` (discrete, continuous, or mixed) residualize X and
Y linearly on `[1, Z]` and need no configuration. `Pillai` is the mixed-data test:
a categorical variable with K levels is regressed as K−1 indicator columns (a
linear probability model).

The root
[README](https://github.com/pgmpy/FastCIT/blob/main/README.md) is the
canonical API guide. See the root
[CONTRIBUTING.md](https://github.com/pgmpy/FastCIT/blob/main/CONTRIBUTING.md)
for development and contribution instructions.
