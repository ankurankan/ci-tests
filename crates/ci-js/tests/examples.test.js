// Runs every documentation example with node and checks that it prints a
// p-value. The examples `require("fastcit")`, so the built pkg/ is copied to a
// temporary node_modules/fastcit and exposed through NODE_PATH.

import { describe, test, expect, beforeAll, afterAll } from "vitest";
import { execFileSync } from "node:child_process";
import { cpSync, mkdtempSync, readdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const examplesDir = join(root, "examples");
const files = readdirSync(examplesDir)
  .filter((f) => f.endsWith(".js"))
  .sort();

let sandbox;
let nodePath;

beforeAll(() => {
  sandbox = mkdtempSync(join(tmpdir(), "fastcit-examples-"));
  nodePath = join(sandbox, "node_modules");
  cpSync(join(root, "pkg"), join(nodePath, "fastcit"), { recursive: true });
});

afterAll(() => {
  rmSync(sandbox, { recursive: true, force: true });
});

describe("documentation examples", () => {
  test("all twelve examples exist", () => {
    expect(files).toHaveLength(12);
  });

  test.each(files)("%s prints a p-value", (file) => {
    const out = execFileSync(process.execPath, [join(examplesDir, file)], {
      env: { ...process.env, NODE_PATH: nodePath },
      encoding: "utf8",
    });
    const lines = out.trim().split(/\r?\n/);
    expect(lines).toHaveLength(1);
    const p = Number(lines[0]);
    expect(p).toBeGreaterThanOrEqual(0);
    expect(p).toBeLessThanOrEqual(1);
    // hsic uses dependent data; a small pearson_equivalence p-value supports
    // equivalence; all other examples use conditionally independent data.
    if (file === "hsic.js") expect(p).toBeLessThan(0.001);
    else if (file === "pearson_equivalence.js") expect(p).toBeLessThan(0.05);
    else expect(p).toBeGreaterThan(0.05);
  });
});
