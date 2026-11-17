"""Checks for the documentation examples, examples/*.pycon.

The examples are doctest transcripts: each shows the four fields of its result and their output.
pytest runs them as doctests (pyproject.toml: --doctest-glob and doctest_optionflags). With the
NUMBER option, a number in the shown output matches to the precision written there.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
FILES = sorted(EXAMPLES.glob("*.pycon"))
PYPROJECT = EXAMPLES.parent / "pyproject.toml"
FIELDS = ("statistic", "p_value", "dof", "effect_size")


def test_all_twelve_examples_exist() -> None:
    assert len(FILES) == 12
    assert not list(EXAMPLES.glob("*.py")), "an example must be a transcript, so that pytest runs it"


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_example_shows_every_result_field(path: Path) -> None:
    """Each field has a prompt line and an output line. A bare None shows no output, so it needs print()."""
    lines = path.read_text(encoding="utf-8").splitlines()
    for field in FIELDS:
        prompts = [i for i, line in enumerate(lines) if line in (f">>> result.{field}", f">>> print(result.{field})")]
        assert len(prompts) == 1, f"{path.name}: show result.{field} once"
        output = lines[prompts[0] + 1] if prompts[0] + 1 < len(lines) else ""
        assert output.strip(), f"{path.name}: result.{field} has no output line"
        assert not output.startswith((">>>", "...")), f"{path.name}: result.{field} has no output line"


@pytest.mark.parametrize(
    ("shown", "passes"),
    [
        ("0.1235", True),  # 0.123456789 at 4 significant digits
        ("0.1234", True),  # one unit in the last written digit is tolerated (NUMBER semantics)
        ("0.1245", False),  # a wrong digit
        ("1.235e-12", True),
        ("1.245e-12", False),
    ],
)
def test_doctest_numbers_match_to_the_written_precision(tmp_path: Path, shown: str, passes: bool) -> None:
    """Run a transcript with the doctest options of pyproject.toml, as pytest runs the examples."""
    value = "1.23456789e-12" if "e" in shown else "0.123456789"
    transcript = tmp_path / "number.pycon"
    transcript.write_text(f">>> {value}\n{shown}\n", encoding="utf-8")
    command = [sys.executable, "-m", "pytest", "-c", str(PYPROJECT), "--rootdir", str(tmp_path), str(transcript)]
    run = subprocess.run([*command, "-q", "-p", "no:cacheprovider"], capture_output=True, text=True, check=False)  # noqa: S603
    assert (run.returncode == 0) == passes, run.stdout
    assert ("1 passed" if passes else "1 failed") in run.stdout, run.stdout
