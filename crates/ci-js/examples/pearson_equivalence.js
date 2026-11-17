const { Dataset, PearsonEquivalence } = require("fastcit");

// Each language makes its own random data, so the values differ from the other tabs.
// Seeded generator (Park-Miller), so every run gives the same data.
let seed = 12345;
const uniform = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
const normal = () =>
  Math.sqrt(-2 * Math.log(uniform())) * Math.cos(2 * Math.PI * uniform());
const draw = (n, f) => Array.from({ length: n }, f);

const n = 2000;
const z = draw(n, normal);
const x = z.map((v) => v + normal()); // X and Y depend on Z only
const y = z.map((v) => v + normal());

const data = new Dataset({
  X: { kind: "continuous", values: x },
  Y: { kind: "continuous", values: y },
  Z: { kind: "continuous", values: z },
});

// A small p-value supports equivalence: |rho| < threshold, so X and Y are independent given Z.
const test = new PearsonEquivalence(data, { deltaThreshold: 0.1 });
const result = test.runTest("X", "Y", ["Z"]);
console.log(result.statistic);
// -0.01296
console.log(result.pValue);
// 0.00004734
console.log(result.dof);
// null
console.log(result.effectSize);
// 0.01296
