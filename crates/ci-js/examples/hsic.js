const { Dataset, HSIC } = require("fastcit");

// Each language makes its own random data, so the values differ from the other tabs.
// Seeded generator (Park-Miller), so every run gives the same data.
let seed = 12345;
const uniform = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
const normal = () =>
  Math.sqrt(-2 * Math.log(uniform())) * Math.cos(2 * Math.PI * uniform());
const draw = (n, f) => Array.from({ length: n }, f);

const n = 300;
const x = draw(n, normal);
const y = x.map((v) => v * v + 0.5 * normal()); // nonlinear, zero correlation

const data = new Dataset({
  X: { kind: "continuous", values: x },
  Y: { kind: "continuous", values: y },
});

const test = new HSIC(data, { bandwidth: "median" });
const result = test.runTest("X", "Y", []);
console.log(result.statistic);
// 2488.9
console.log(result.pValue);
// 1.902e-38
console.log(result.dof);
// null
console.log(result.effectSize);
// 0.3257
