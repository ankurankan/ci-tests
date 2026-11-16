# ci-core

`ci-core` is the dependency-light Rust implementation of data-bound
conditional-independence testing.

## API

Build a [`Dataset`](src/dataset.rs) from named discrete or continuous columns,
then pass it to a stateless test implementing [`CITest`](src/strategy.rs):
`test(&data, x, y, z)` returns the test result, while
`is_independent(&data, x, y, z, alpha)` returns an independence decision.

The ten implementations are `ChiSquared`, `LogLikelihood`, `CressieRead`,
`FreemanTukey`, `ModifiedLikelihood`, `PearsonCorrelation`, `FisherZ`, and
`PearsonEquivalence`, `Hsic`, and `Kci`.

`Hsic` and `Kci` are kernel tests (RBF and linear kernels, configured through
`KernelChoice` and `Bandwidth`). `Hsic` is unconditional; `Kci` conditions on
`z` at O(n²) memory and O(n³) time.

The root
[README](https://github.com/pgmpy/ci-tests/blob/main/README.md) is the
canonical API guide. See the root
[CONTRIBUTING.md](https://github.com/pgmpy/ci-tests/blob/main/CONTRIBUTING.md)
for development and contribution instructions.
