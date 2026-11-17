const { Dataset, ChiSquared } = require("fastcit");

// Seeded generator (Park-Miller), so every run gives the same data.
let seed = 12345;
const uniform = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
const draw = (n, f) => Array.from({ length: n }, f);

const n = 500;
const z = draw(n, () => Math.floor(uniform() * 3));
// X and Y each copy Z about 40% of the time, so they depend on Z only.
const copy = (v) => (uniform() < 0.4 ? v : Math.floor(uniform() * 3));
const x = z.map(copy);
const y = z.map(copy);

const data = new Dataset({
  X: { kind: "discrete", values: x },
  Y: { kind: "discrete", values: y },
  Z: { kind: "discrete", values: z },
});

const test = new ChiSquared(data);
const result = test.runTest("X", "Y", ["Z"]);
console.log(result.pValue);
