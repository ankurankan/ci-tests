# ci-js

WebAssembly bindings for the data-bound conditional-independence API.

## Usage

Build the Node.js package from the repository root:

```sh
wasm-pack build crates/ci-js --target nodejs
```

```js
import { Dataset, PearsonCorrelation } from "./pkg/ci_js.js";

const data = new Dataset({
  X: { kind: "continuous", values: [0.2, 0.8, 1.4, 2.1, 2.7] },
  Y: { kind: "continuous", values: [1.0, 1.7, 2.5, 3.0, 3.8] },
});
const result = new PearsonCorrelation(data).runTest("X", "Y", []);
```

### Kernel tests (HSIC, KCI)

```js
import { Dataset, HSIC, KCI } from "./pkg/ci_js.js";

const hsic = new HSIC(data, {
  kernel: { type: "rbf", lengthScale: 1.0 }, // or `kernels: { X: {...}, Y: {...} }`
  bandwidth: "median", // "heuristic" (default) | "median"
  nullDist: "permutation", // "gamma" (default) | "permutation"
  nPermutations: 200, // positive safe integer (default 100)
  seed: 7, // safe integer >= 0 (default 0)
});
hsic.runTest("X", "Y", []); // HSIC takes no conditioning set

const kci = new KCI(data, { epsilon: 1e-3 });
kci.runTest("X", "Y", ["Z"]);
```

`kernel` and `kernels` are mutually exclusive; invalid options throw.

### Residual-based tests (GCM, PillaiTrace)

```js
import { Dataset, GCM, PillaiTrace } from "./pkg/ci_js.js";

new GCM(data).runTest("X", "Y", ["Z"]); // continuous columns only
new PillaiTrace(data).runTest("X", "Y", ["Z"]); // mixed discrete/continuous
```

Neither class takes options (unknown keys throw). Both residualize with linear
regression (pgmpy's Pillai default is a random forest). In PillaiTrace,
conditioning variables enter as one-hot columns minus one level; a categorical X or Y becomes K-1 level
indicators, residualized with a linear probability model. Canonical
correlations are computed exactly. Degenerate inputs throw instead of returning
NaN (both tests). Conditioning sets whose columns are linearly dependent (duplicate or nested categorical variables, a constant column) raise a degenerate-data error, whereas pgmpy fits them by least squares. With few rows relative to the conditioning columns and
categorical levels (`n - columns < p + q`), PillaiTrace returns `p = 0`
("dependent"), as pgmpy does. GCM is continuous-only; a discrete X, Y or Z
throws.

Run the JavaScript checks from the package directory:

```sh
npm ci
npm test
```

For browser builds, the complete API, and contribution guidance, see the root
[README](../../README.md) and [CONTRIBUTING.md](../../CONTRIBUTING.md).
