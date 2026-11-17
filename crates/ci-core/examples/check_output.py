"""Compare the output of a Rust example with the output comments in its source.

Each example prints the four fields of its result. The `//` comment lines right under each
`println!` line show its output. A number in a comment matches to the precision written there,
as with the NUMBER option of pytest doctests.
Thus 0.5778 matches 0.5778219788, but 0.5768 does not.

Usage (the "Run examples" step of .github/workflows/rust.yml):

    cargo run -q -p fastcit-core --example fisher_z | python check_output.py fisher_z.rs

Test this script with `python -m doctest check_output.py`:

>>> lines_match("Some(0.5778)", "Some(0.5778219788056369)")  # 4 significant digits
True
>>> lines_match("Some(0.5778)", "Some(0.5778619788056369)")  # differs beyond the written precision
True
>>> lines_match("Some(0.5768)", "Some(0.5778219788056369)")  # a wrong digit
False
>>> lines_match("1.716e-42", "1.7158766982475783e-42")
True
>>> lines_match("1.726e-42", "1.7158766982475783e-42")
False
>>> lines_match("Some(12)", "Some(13)")  # integers match as text
False
>>> lines_match("None", "Some(0.5778)")
False
>>> shown_output(["let x = 1; // a comment", "println!(x);", "// 1", "println!(y);", "// 2", "// 3"])
['1', '2', '3']
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

FIELDS = ("statistic", "p_value", "dof", "effect_size")
# A number with a decimal point or an exponent, as in pytest's NUMBER option. Integers match as text.
NUMBER = re.compile(r"[+-]?(?:\d*\.(?P<fraction>\d+)|\d+\.)(?:[eE](?P<exp1>[+-]?\d+))?|[+-]?\d+[eE](?P<exp2>[+-]?\d+)")


def lines_match(want: str, got: str) -> bool:
    """Return True when `got` is `want`, with each number of `want` equal to its written precision."""
    want, got = want.rstrip(), got.rstrip()
    wants, gots = list(NUMBER.finditer(want)), list(NUMBER.finditer(got))
    if len(wants) != len(gots) or NUMBER.sub("", want) != NUMBER.sub("", got):
        return False
    for w, g in zip(wants, gots):
        unit = 10.0 ** (int(w["exp1"] or w["exp2"] or 0) - len(w["fraction"] or ""))
        if abs(float(w[0]) - float(g[0])) > max(unit, 1e-6 * abs(float(g[0]))):
            return False
    return True


def shown_output(lines: list[str]) -> list[str]:
    """Return the `//` comment lines under each `println!` line, without the `//` mark."""
    shown: list[str] = []
    after_print = False
    for line in map(str.strip, lines):
        if after_print and line.startswith("//"):
            shown.append(line[2:].strip())
        else:
            after_print = line.startswith("println!(")
    return shown


def main(example: str) -> int:
    """Compare the standard input with the output comments of `example`; return the exit status."""
    got = sys.stdin.read().splitlines()
    lines = Path(example).read_text(encoding="utf-8").splitlines()
    code = [line.strip() for line in lines]
    missing = [field for field in FIELDS if f'println!("{{:?}}", result.{field});' not in code]
    if missing:
        print(f"{example}: print every field of the result, missing:", *missing)
        return 1
    want = shown_output(lines)
    if len(want) == len(got) and all(map(lines_match, want, got)):
        print(f"{example}: the output matches the {len(want)} output comments")
        return 0
    print(f"{example}: the output does not match the output comments")
    print("shown:", *want, sep="\n  ")
    print("output:", *got, sep="\n  ")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
