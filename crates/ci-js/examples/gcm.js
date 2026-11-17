const { Dataset, GCM } = require("fastcit");

// Seeded generator (Park-Miller), so every run gives the same data.
let seed = 12345;
const uniform = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
const normal = () =>
  Math.sqrt(-2 * Math.log(uniform())) * Math.cos(2 * Math.PI * uniform());
const draw = (n, f) => Array.from({ length: n }, f);

const n = 500;
const z = draw(n, normal);
const x = z.map((v) => v + normal()); // X and Y depend on Z only
const y = z.map((v) => v + normal());

const data = new Dataset({
  X: { kind: "continuous", values: x },
  Y: { kind: "continuous", values: y },
  Z: { kind: "continuous", values: z },
});

const test = new GCM(data);
const result = test.runTest("X", "Y", ["Z"]);
console.log(result.pValue);
