// Runs every documentation example with node. Each example prints the four
// fields of its result, and the `//` comments right under each console.log
// line show the output. The tests compare the output with those comments. A
// number in a comment matches to the precision written there, as with the
// NUMBER option of pytest doctests: 0.5778 matches 0.5778219788.
// The examples `require("fastcit")`, so the built pkg/ is copied to a
// temporary node_modules/fastcit and exposed through NODE_PATH.

import { describe, test, expect, beforeAll, afterAll } from "vitest";
import { execFileSync } from "node:child_process";
import {
  cpSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  rmSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

// A number with a decimal point or an exponent, as in the NUMBER option of
// pytest doctests. Integers are not numbers here: they match as text.
// Groups: 1 the fraction, 2 and 3 the exponent.
const NUMBER =
  /[+-]?(?:\d*\.(\d+)|\d+\.)(?:[eE]([+-]?\d+))?|[+-]?\d+[eE]([+-]?\d+)/g;

// True when the output line `got` is the shown line `want`. As with pytest's
// NUMBER option, each number of `want` matches to its written precision.
const outputMatches = (want, got) => {
  const wants = [...want.trimEnd().matchAll(NUMBER)];
  const gots = [...got.trimEnd().matchAll(NUMBER)];
  const sameText =
    want.trimEnd().replace(NUMBER, "") === got.trimEnd().replace(NUMBER, "");
  if (wants.length !== gots.length || !sameText) return false;
  return wants.every((w, i) => {
    const value = Number(gots[i][0]);
    const exponent = Number(w[2] ?? w[3] ?? 0);
    const unit = 10 ** (exponent - (w[1] ?? "").length);
    const tolerance = Math.max(unit, 1e-6 * Math.abs(value));
    return Math.abs(Number(w[0]) - value) <= tolerance;
  });
};

// The shown output: the `//` comment lines under each console.log line,
// without the "// " mark.
const shownOutput = (lines) => {
  const shown = [];
  let afterLog = false;
  for (const line of lines) {
    if (afterLog && line.startsWith("//")) {
      shown.push(line.replace(/^\/\/ ?/, ""));
    } else {
      afterLog = line.startsWith("console.log(");
    }
  }
  return shown;
};

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

  test.each(files)("%s shows its output", (file) => {
    const path = join(examplesDir, file);
    const lines = readFileSync(path, "utf8").split(/\r?\n/);
    for (const field of ["statistic", "pValue", "dof", "effectSize"]) {
      expect(lines).toContain(`console.log(result.${field});`);
    }
    const shown = shownOutput(lines);
    const out = execFileSync(process.execPath, [path], {
      env: { ...process.env, NODE_PATH: nodePath },
      encoding: "utf8",
    });
    const printed = out.trimEnd().split(/\r?\n/);
    expect(printed).toHaveLength(shown.length);
    shown.forEach((want, i) => {
      const message = `shows ${want}, but prints ${printed[i]}`;
      expect(outputMatches(want, printed[i]), message).toBe(true);
    });
  });
});

describe("output comments", () => {
  test("shown numbers match to the written precision", () => {
    // 0.5778 is 0.5778219 at 4 significant digits. The digits after the 4th
    // do not count, but a wrong digit before them does.
    expect(outputMatches("0.5778", "0.5778219788056369")).toBe(true);
    expect(outputMatches("0.5778", "0.5778619788056369")).toBe(true);
    expect(outputMatches("0.5768", "0.5778219788056369")).toBe(false);
    expect(outputMatches("1.716e-42", "1.7158766982475783e-42")).toBe(true);
    expect(outputMatches("1.726e-42", "1.7158766982475783e-42")).toBe(false);
    // Integers and other text match exactly.
    expect(outputMatches("12", "12")).toBe(true);
    expect(outputMatches("12", "13")).toBe(false);
    expect(outputMatches("null", "null")).toBe(true);
    expect(outputMatches("null", "0.5778")).toBe(false);
  });

  test("the output comments are the // lines under a console.log line", () => {
    const lines = [
      "// a comment",
      "const x = 1; // a comment",
      "console.log(x);",
      "// 1",
      "console.log([x, x]);",
      "// [ 1,",
      "//   1 ]",
      "// a comment",
    ];
    expect(shownOutput(lines)).toEqual(["1", "[ 1,", "  1 ]", "a comment"]);
  });
});
