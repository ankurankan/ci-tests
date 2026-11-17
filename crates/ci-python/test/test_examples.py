"""Run every documentation example and check that it prints a valid p-value."""

from __future__ import annotations

import runpy
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
FILES = sorted(EXAMPLES.glob("*.py"))

# Seeded examples are deterministic. Dependent data (HSIC) must give a tiny p-value,
# the equivalence test must reject non-equivalence (p < 0.05), and every other
# example uses conditionally independent data (p > 0.05).
DEPENDENT = {"hsic": 0.001}
EQUIVALENT = {"pearson_equivalence": 0.05}


def test_all_twelve_examples_exist() -> None:
    assert len(FILES) == 12


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_example_prints_p_value(path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runpy.run_path(str(path), run_name="__main__")
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 1
    p = float(lines[-1])
    assert 0.0 <= p <= 1.0
    if path.stem in DEPENDENT:
        assert p < DEPENDENT[path.stem]
    elif path.stem in EQUIVALENT:
        assert p < EQUIVALENT[path.stem]
    else:
        assert p > 0.05
