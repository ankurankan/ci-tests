"""Checks for the documentation home page in docs/site/.

The page repeats the install commands and the quick start examples of the README.
These tests fail when the two copies differ. They also check that the page data
(benchmarks/results/summary.json) matches the benchmark results and that the docs
workflow publishes the page.
"""

from __future__ import annotations

import html
import importlib.util
import json
import re
import shutil
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SITE = REPO_ROOT / "docs" / "site"
README = REPO_ROOT / "README.md"
RESULTS = REPO_ROOT / "benchmarks" / "results"
LANGUAGES = {"python": "Python", "r": "R", "javascript": "JavaScript", "rust": "Rust"}


def page() -> str:
    return (SITE / "index.html").read_text(encoding="utf-8")


def readme() -> str:
    return README.read_text(encoding="utf-8")


def page_code(attribute: str, language: str) -> str:
    """Return the unescaped text of the page's <code ATTRIBUTE="LANGUAGE"> block."""
    found = re.findall(rf'<code [^>]*\b{attribute}="{language}"[^>]*>(.*?)</code>', page(), re.S)
    assert len(found) == 1, f"expected one <code {attribute}={language!r}> block in index.html"
    return html.unescape(found[0])


def readme_example(name: str) -> str:
    """Return the fenced code block in the README's <details> block for one language."""
    found = re.findall(rf"<summary>{re.escape(name)}</summary>\s*```[A-Za-z]*\n(.*?)\n```", readme(), re.S)
    assert len(found) == 1, f"expected one {name} example in README.md"
    return found[0]


def readme_install(name: str) -> str:
    found = re.findall(rf"^\| {re.escape(name)} \| `([^`]+)` \|$", readme(), re.M)
    assert len(found) == 1, f"expected one {name} row in the README install table"
    return found[0]


@pytest.mark.parametrize("language", LANGUAGES)
def test_quick_start_example_matches_readme(language: str) -> None:
    assert page_code("data-snippet", language) == readme_example(LANGUAGES[language])


@pytest.mark.parametrize("language", LANGUAGES)
def test_install_command_matches_readme(language: str) -> None:
    assert page_code("data-install", language) == readme_install(LANGUAGES[language])


def test_page_uses_relative_links_for_the_api_reference() -> None:
    text = page()
    for target in ("rust/fastcit_core/index.html", "r/index.html", "python/fastcit.html", "js/index.html"):
        assert f'href="{target}"' in text
    assert 'data-src="benchmarks.json"' in text
    for local in re.findall(r'(?:href|src)="([^"]+)"', text):
        assert not local.startswith("/"), f"{local} breaks under the /FastCIT/ sub-path"


def test_summary_json_matches_the_benchmark_results(tmp_path: Path) -> None:
    """summary.json and summary.md must be the output of summarize.py for the committed run files."""
    runs = [path for path in RESULTS.glob("*.json") if path.name != "summary.json"]
    assert runs, "benchmarks/results holds no run files"
    for path in runs:
        shutil.copy(path, tmp_path / path.name)
    spec = importlib.util.spec_from_file_location("summarize", REPO_ROOT / "benchmarks" / "summarize.py")
    assert spec is not None and spec.loader is not None
    summarize = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(summarize)
    summarize.main(tmp_path)
    assert (tmp_path / "summary.md").read_text(encoding="utf-8") == (RESULTS / "summary.md").read_text(
        encoding="utf-8"
    )
    assert json.loads((tmp_path / "summary.json").read_text(encoding="utf-8")) == json.loads(
        (RESULTS / "summary.json").read_text(encoding="utf-8")
    )


def test_cells_carry_the_run_spread() -> None:
    """Each cell with a result has its run values; a cell gets the mark † exactly when its range exceeds the limit."""
    data = json.loads((RESULTS / "summary.json").read_text(encoding="utf-8"))
    for eco in data["ecosystems"]:
        limit = eco["spread"]["limit"]
        for table in (eco["per_call"], eco["total_per_pass"]):
            for row in table["rows"]:
                for cell in row["cells"]:
                    if cell["value"] is None:
                        continue
                    assert len(cell["runs"]) == eco["spread"]["runs"]
                    assert cell["min"] <= cell["value"] <= cell["max"]
                    assert cell["flagged"] == (cell["spread"] > limit) == ("†" in cell["marks"])


def test_summary_json_has_the_fields_the_page_reads() -> None:
    data = json.loads((RESULTS / "summary.json").read_text(encoding="utf-8"))
    assert data["ecosystems"]
    for eco in data["ecosystems"]:
        assert {"key", "label", "meta", "per_call", "total_per_pass"} <= eco.keys()
        assert {"date", "cpu", "os", "versions", "passes"} <= eco["meta"].keys()
        for table in (eco["per_call"], eco["total_per_pass"]):
            assert any(column["key"] == "fastcit" for column in table["columns"])
            marks = {note["mark"] for note in table["footnotes"]}
            for row in table["rows"]:
                assert len(row["cells"]) == len(table["columns"])
                for cell in row["cells"]:
                    assert cell["value"] is None or cell["value"] > 0
                    assert set(cell["marks"]) <= marks, f"{row['key']}: a mark has no footnote"
                assert set(row["marks"]) <= marks


def test_fastcit_takes_palette_slot_one_by_key() -> None:
    """Every table has a `fastcit` column, and the page gives that key slot 1 whatever its position."""
    data = json.loads((RESULTS / "summary.json").read_text(encoding="utf-8"))
    for eco in data["ecosystems"]:
        for table in (eco["per_call"], eco["total_per_pass"]):
            assert [column["key"] for column in table["columns"]].count("fastcit") == 1
    script = (SITE / "site.js").read_text(encoding="utf-8")
    assert 'var FOCUS_KEY = "fastcit";' in script
    assert re.search(r"column\.key === FOCUS_KEY \? 0 : next\+\+", script), "assignSlots must give FOCUS_KEY slot 0"
    # No call may colour a package by its column index.
    assert not re.search(r"slotClass\((i|mark\.index)\)", script)
    assert not re.search(r"swatch\(i,", script)


def test_page_shows_the_other_runs_and_the_run_range() -> None:
    """The page names each extra interpreter with its versions, and the tooltip gives the run range."""
    data = json.loads((RESULTS / "summary.json").read_text(encoding="utf-8"))
    python = next(eco for eco in data["ecosystems"] if eco["key"] == "python")
    for other in python["meta"]["other_runs"]:
        assert {"python", "versions", "engines", "runs"} <= other.keys()
    script = (SITE / "site.js").read_text(encoding="utf-8")
    assert "meta.other_runs" in script
    assert "mark.cell.range_text" in script
    assert 'plural(compared, "compared test")' in script


def test_docs_workflow_publishes_the_home_page() -> None:
    text = (REPO_ROOT / ".github" / "workflows" / "docs.yml").read_text(encoding="utf-8")
    workflow = yaml.safe_load(text)
    # PyYAML reads the bare key `on` as the boolean True.
    paths = workflow[True]["push"]["paths"]
    for path in ("docs/site/**", "benchmarks/results/**", "README.md"):
        assert path in paths
    steps = workflow["jobs"]["deploy"]["steps"]
    assert steps[0].get("uses", "").startswith("actions/checkout@")
    commands = "\n".join(step.get("run", "") for step in steps)
    assert "docs/site/" in commands
    assert "benchmarks/results/summary.json site/benchmarks.json" in commands
    assert "cat > site/index.html" not in commands
