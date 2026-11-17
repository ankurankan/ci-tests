"""Checks for the documentation site in docs/ (Sphinx, MyST pages), published at https://pgmpy.org/FastCIT/.

The home page repeats the install commands of the README. The Quickstart of the home page and of the
README is the Fisher-z example file of each language. These tests fail when a copy differs.
The home page includes the two tables of median call times from benchmarks/results/summary.md. Each test page must show the CI-run example file of each language
in a synced language tab set. The Benchmark page shows the chart of benchmarks/results/sweep.json,
or a notice when the file does not exist. The tests also check the benchmark summary and the docs workflow.

The tests at the end build the site with Sphinx. They skip when the Sphinx stack of
docs/requirements.txt is not installed (for example in the golden-fixture job of python.yml).
"""

from __future__ import annotations

import ast
import html
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from fnmatch import fnmatch
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = REPO_ROOT / "docs"
INDEX = DOCS / "index.md"
BENCHMARK = DOCS / "benchmark.md"
TEST_PAGES = DOCS / "tests"
STATIC = DOCS / "_static"
README = REPO_ROOT / "README.md"
RESULTS = REPO_ROOT / "benchmarks" / "results"
SWEEP_JSON = RESULTS / "sweep.json"
CHART_JS = STATIC / "sweep-chart.js"
CHART_CSS = STATIC / "sweep-chart.css"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "docs.yml"
CHECK_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "docs-check.yml"
# Set in docs-check.yml: there the Sphinx tests must run, not skip.
REQUIRE_SPHINX = os.environ.get("FASTCIT_DOCS_REQUIRE_SPHINX") == "1"

LANGUAGES = {"python": "Python", "r": "R", "javascript": "JavaScript", "rust": "Rust"}
EXAMPLES = {
    "python": "crates/ci-python/examples/{key}.pycon",
    "r": "crates/ci-r/inst/examples/tests/{key}.R",
    "javascript": "crates/ci-js/examples/{key}.js",
    "rust": "crates/ci-core/examples/{key}.rs",
}
# The Pygments lexer of each example file. The Python examples are doctest transcripts.
LEXERS = {"python": "pycon", "r": "r", "javascript": "javascript", "rust": "rust"}
# The copy button of a code block removes these prompts (copybutton_prompt_text in docs/conf.py).
COPY_PROMPT = r">>> |\.\.\. "
# key: (Python and JavaScript class, R function, Rust type)
TESTS = {
    "chi_squared": ("ChiSquared", "chi_squared", "ChiSquared"),
    "log_likelihood": ("LogLikelihood", "log_likelihood", "LogLikelihood"),
    "cressie_read": ("CressieRead", "cressie_read", "CressieRead"),
    "freeman_tukey": ("FreemanTukey", "freeman_tukey", "FreemanTukey"),
    "modified_likelihood": ("ModifiedLikelihood", "modified_likelihood", "ModifiedLikelihood"),
    "pearson_correlation": ("PearsonCorrelation", "pearson_correlation", "PearsonCorrelation"),
    "fisher_z": ("FisherZ", "fisher_z", "FisherZ"),
    "pearson_equivalence": ("PearsonEquivalence", "pearson_equivalence", "PearsonEquivalence"),
    "hsic": ("HSIC", "hsic", "Hsic"),
    "kci": ("KCI", "kci", "Kci"),
    "gcm": ("GCM", "gcm", "Gcm"),
    "pillai": ("PillaiTrace", "pillai", "Pillai"),
}
TEST_PAGE_HEADINGS = ["Usage", "Method"]
# The constructor line of each language tab: key -> (template, field of TESTS).
SIGNATURES = {
    "python": "`fastcit.{0}(",
    "r": "`{1}(",
    "javascript": "`new {0}(",
    "rust": "`fastcit_core::ci_tests::{2}",
}
# The home page includes these parts of summary.md: (start-after, end-before) per language tab.
RUNTIME_TABLES = {
    "python": ("## Python packages, median time of one call", "## R packages, median time of one call"),
    "r": ("## R packages, median time of one call", "## Python packages, total time of one pass"),
}
# The relative targets of the API reference cards. The deploy job adds these sites next to the Sphinx output.
API_TARGETS = ("python/fastcit.html", "r/index.html", "js/index.html", "rust/fastcit_core/index.html")
# The navbar of every page: the hidden toctree of the home page.
NAVBAR = ["CI Tests", "Benchmark", "API reference"]
# The notice of the Benchmark page when sweep.json does not exist.
SWEEP_NOTICE = "The benchmark results are not available at this time."
# External URLs that a page may contain.
ALLOWED_EXTERNAL = (
    "https://github.com/pgmpy/FastCIT",
    "https://pgmpy.org/",
    "https://cdn.jsdelivr.net/npm/mathjax@",
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def readme_example(name: str) -> str:
    """Return the fenced code block in the README's <details> block for one language."""
    found = re.findall(rf"<summary>{re.escape(name)}</summary>\s*```[A-Za-z]*\n(.*?)\n```", read(README), re.S)
    assert len(found) == 1, f"expected one {name} example in README.md"
    return found[0]


def readme_install(name: str) -> str:
    found = re.findall(rf"^\| {re.escape(name)} \| `([^`]+)` \|$", read(README), re.M)
    assert len(found) == 1, f"expected one {name} row in the README install table"
    return found[0]


def section(text: str, heading: str) -> str:
    """Return the Markdown of the level-2 section `heading`, up to the next level-2 heading."""
    found = re.findall(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    assert len(found) == 1, f"expected one section '## {heading}'"
    return found[0]


def tab_items(markdown: str) -> list[tuple[str, str, str]]:
    """Return (label, sync key, body) for each tab item of the one tab set in `markdown`."""
    sets = re.findall(r"^::::\{tab-set\}\n(.*?)^::::$", markdown, re.S | re.M)
    assert len(sets) == 1, "expected one tab set"
    assert sets[0].startswith(":sync-group: language\n"), "the tab set must use the sync group 'language'"
    return re.findall(r"^:::\{tab-item\} (.+?)\n:sync: (\S+)\n(.*?)^:::$", sets[0], re.S | re.M)


def fenced_code(body: str) -> str:
    found = re.findall(r"^```[A-Za-z]*\n(.*?)\n```$", body, re.S | re.M)
    assert len(found) == 1, "expected one code block in the tab"
    return found[0]


# ------------------------------------------------------------------- home page


@pytest.mark.parametrize("language", LANGUAGES)
def test_quickstart_includes_the_fisher_z_example(language: str) -> None:
    items = {key: body for _, key, body in tab_items(section(read(INDEX), "Quickstart"))}
    example = EXAMPLES[language].format(key="fisher_z")
    includes = re.findall(r"^```\{literalinclude\} (\S+)\n:language: (\S+)\n", items[language], re.M)
    assert includes == [(f"../{example}", LEXERS[language])]
    assert (REPO_ROOT / example).is_file()


@pytest.mark.parametrize("language", LANGUAGES)
def test_readme_quickstart_is_the_fisher_z_example(language: str) -> None:
    example = read(REPO_ROOT / EXAMPLES[language].format(key="fisher_z"))
    assert readme_example(LANGUAGES[language]) + "\n" == example


@pytest.mark.parametrize("language", LANGUAGES)
def test_install_command_matches_readme(language: str) -> None:
    items = {key: body for _, key, body in tab_items(section(read(INDEX), "Install"))}
    assert fenced_code(items[language]) == readme_install(LANGUAGES[language])


@pytest.mark.parametrize("heading", ["Install", "Quickstart", "One API for all tests"])
def test_home_page_tabs_use_the_language_keys(heading: str) -> None:
    items = tab_items(section(read(INDEX), heading))
    assert [(label, key) for label, key, _ in items] == [(label, key) for key, label in LANGUAGES.items()]


def test_home_page_lists_every_test_page() -> None:
    table = read(DOCS / "_includes" / "test-table.md")
    assert re.findall(r"</tests/(\w+)>", table) == list(TESTS)
    assert "_includes/test-table.md" in read(INDEX)
    assert "../_includes/test-table.md" in read(TEST_PAGES / "index.md")
    toctree = re.findall(r"```\{toctree\}\n(.*?)```", read(TEST_PAGES / "index.md"), re.S)
    assert len(toctree) == 1
    assert [line for line in toctree[0].splitlines() if line and not line.startswith(":")] == list(TESTS)


def test_api_cards_use_relative_links() -> None:
    cards = read(DOCS / "_includes" / "api-cards.md")
    assert re.findall(r"^:link: (\S+)$", cards, re.M) == list(API_TARGETS)
    for page in (INDEX, DOCS / "api.md"):
        assert "_includes/api-cards.md" in read(page)


def test_home_page_includes_the_runtime_tables() -> None:
    items = tab_items(section(read(INDEX), "Runtime Comparison"))
    assert [(label, key) for label, key, _ in items] == [("Python", "python"), ("R", "r")]
    summary = read(RESULTS / "summary.md")
    for _, key, body in items:
        start, end = RUNTIME_TABLES[key]
        include = re.findall(r'^```\{include\} (\S+)\n:start-after: "(.+)"\n:end-before: "(.+)"\n```$', body, re.M)
        assert include == [("../benchmarks/results/summary.md", start, end)], key
        # Each marker must occur, and the first match of the end marker must follow the start marker.
        assert summary.index(start) < summary.index(end, summary.index(start))


def test_navbar_order() -> None:
    toctree = re.findall(r"```\{toctree\}\n:hidden:\n\n(.*?)```", read(INDEX), re.S)
    assert len(toctree) == 1
    assert [line.split(" <")[0] for line in toctree[0].splitlines() if line] == NAVBAR


# -------------------------------------------------------------- benchmark page


def test_benchmark_page_has_little_prose() -> None:
    """A title, the chart (or the notice), and a method note of at most 6 short sentences (ASD-STE100)."""
    text = read(BENCHMARK)
    assert re.findall(r"^(#+) (.+)$", text, re.M) == [("#", "Benchmark"), ("##", "Method")]
    method = " ".join(section(text, "Method").split())
    sentences = re.split(r"(?<=\.) (?=[A-Z])", method)
    assert 1 <= len(sentences) <= 6, sentences
    for sentence in sentences:
        assert len(sentence.split()) <= 25, sentence
    assert "(https://github.com/pgmpy/FastCIT/blob/main/benchmarks/README.md)" in method
    assert "chart" not in method.lower(), "the method shows without data too, so it must not point at the chart"
    # Before the method: the chart host for the build with data, one notice for the build without.
    top = text[: text.index("## Method")]
    assert re.findall(r"^:::\{only\} (.+)$", top, re.M) == ["sweep", "not sweep"]
    assert '<div class="sweep-chart" data-src="sweep.json"></div>' in top
    assert re.search(r"^:::\{only\} not sweep\n\n" + re.escape(SWEEP_NOTICE) + r"\n\n:::$", top, re.M)


def test_chart_reads_only_fields_of_the_schema() -> None:
    """The chart reads sweep.json only through the fields of the schema in summarize_sweep.py.

    The script names the variables that hold parts of sweep.json data, lang, row, sweep, series, meta and run.
    """
    schema = ast.get_docstring(ast.parse(read(REPO_ROOT / "benchmarks" / "summarize_sweep.py")))
    assert schema is not None
    fields = set(re.findall(r'"(\w+)"', schema))
    script = re.sub(r"/\*.*?\*/|//[^\n]*", "", read(CHART_JS), flags=re.S)  # code only, not the comments
    used = set(re.findall(r"(?<![\w.])(?:data|lang|row|sweep|series|meta|run)\.(\w+)", script))
    assert used <= fields, f"not in the schema: {sorted(used - fields)}"
    # A missing point is a gap with its reason; a one-pass point and left-out queries are marked.
    assert {"values", "skipped", "passes", "excluded", "notes", "engine", "label", "fixed", "x"} <= used


def test_chart_colours_every_package() -> None:
    """Each package has a fixed palette slot and marker shape (FastCIT: 1, circle).

    Each slot has a light and a dark colour.
    """
    spec = importlib.util.spec_from_file_location("summarize", REPO_ROOT / "benchmarks" / "summarize.py")
    assert spec is not None and spec.loader is not None
    summarize = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(summarize)
    script = read(CHART_JS)
    found = re.findall(r'"?([\w-]+)"?: \[([1-8]), "(\w+)"\]', re.search(r"var PACKAGES = \{(.*?)\};", script, re.S)[1])
    packages = {key: (slot, shape) for key, slot, shape in found}
    assert packages["fastcit"] == ("1", "circle")
    shapes = set(re.findall(r"^    (\w+): \[\[", re.search(r"var SHAPES = \{(.*?)\};", script, re.S)[1], re.M))
    assert {shape for _, shape in packages.values()} <= shapes | {"circle", "cross"}
    assert "SHAPES.cross = SHAPES.plus" in script
    for cols in (summarize.PY_COLS, summarize.R_COLS):
        engines = [key for key, _ in cols]
        assert set(engines) <= set(packages), f"no slot and shape: {sorted(set(engines) - set(packages))}"
        assert len({packages[key][0] for key in engines}) == len(engines), "two packages of a language share a slot"
        assert len({packages[key] for key in engines}) == len(engines), "two packages share a (colour, shape) pair"
    css = read(CHART_CSS)
    light = re.search(r"^\.sweep-chart \{(.*?)^\}", css, re.S | re.M)[1]
    dark = re.search(r'^html\[data-theme="dark"\] \.sweep-chart \{(.*?)^\}', css, re.S | re.M)[1]
    for block in (light, dark):
        assert re.findall(r"--sweep-(\d): #[0-9a-f]{6};", block) == [str(i) for i in range(1, 9)]
    # Dark mode follows html[data-theme] of the theme, not the browser's colour scheme.
    assert "prefers-color-scheme" not in css


def test_chart_code_stays_small() -> None:
    assert len(read(CHART_JS).splitlines()) <= 520
    assert len(read(CHART_CSS).splitlines()) <= 250


# ------------------------------------------------------------------ test pages


@pytest.mark.parametrize("key", TESTS)
def test_test_page_structure(key: str) -> None:
    text = read(TEST_PAGES / f"{key}.md")
    headings = re.findall(r"^(#{1,3}) (.+)$", text, re.M)
    assert headings[0][0] == "#", "the page starts with its title"
    assert [title for level, title in headings[1:]] == TEST_PAGE_HEADINGS
    assert all(level == "##" for level, _ in headings[1:])
    # The data types come first, right after the title.
    body = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
    assert re.match(r"\s*# .+\n\n:Data types: .+\n:API: .+\(\.\./index\.md#one-api-for-all-tests\)\.\n\n## Usage\n", body), (
        "the data types and the link to the shared API must lead the page"
    )
    for _, language, tab in tab_items(section(text, "Usage")):
        signature = SIGNATURES[language].format(*TESTS[key])
        assert tab.lstrip().startswith(signature), f"{key}, {language}: the tab must start with {signature}"


@pytest.mark.parametrize("key", TESTS)
def test_test_page_includes_the_ci_examples(key: str) -> None:
    items = tab_items(section(read(TEST_PAGES / f"{key}.md"), "Usage"))
    assert [(label, sync) for label, sync, _ in items] == [(label, sync) for sync, label in LANGUAGES.items()]
    for _, language, body in items:
        example = EXAMPLES[language].format(key=key)
        includes = re.findall(r"^```\{literalinclude\} (\S+)\n:language: (\S+)\n", body, re.M)
        assert includes == [(f"../../{example}", LEXERS[language])], f"{key}, {language}: include {example}"
        assert (REPO_ROOT / example).is_file(), f"{example} is missing"


@pytest.mark.parametrize("page", sorted(path.name for path in TEST_PAGES.glob("*.md")))
def test_test_pages_have_no_unexpected_external_links(page: str) -> None:
    for url in re.findall(r"https?://[^\s)>]+", read(TEST_PAGES / page)):
        assert url.startswith(ALLOWED_EXTERNAL), f"{page}: unexpected external URL {url}"


def test_pages_use_no_root_relative_links() -> None:
    """A link that starts with / breaks under the /FastCIT/ sub-path."""
    for path in DOCS.rglob("*.md"):
        text = read(path)
        assert not re.search(r"\]\(/", text), f"{path}: root-relative Markdown link"
        assert not re.search(r'(?:href|src)="/', text), f"{path}: root-relative HTML link"


# ------------------------------------------------------- site configuration


def test_docs_requirements_are_pinned() -> None:
    lines = [line.strip() for line in read(DOCS / "requirements.txt").splitlines()]
    packages = [line for line in lines if line and not line.startswith("#")]
    names = {re.split(r"[=<>!~]", line)[0].lower() for line in packages}
    assert {"sphinx", "pydata-sphinx-theme", "sphinx-design", "myst-parser", "sphinx-copybutton"} <= names
    for line in packages:
        assert re.fullmatch(r"[A-Za-z0-9_.-]+==[0-9][0-9A-Za-z.]*", line), f"not pinned: {line}"


def test_conf_mirrors_the_pgmpy_theme() -> None:
    conf = read(DOCS / "conf.py")
    assert 'html_theme = "pydata_sphinx_theme"' in conf
    assert '"text": "FastCIT"' in conf
    assert 'html_logo = "_static/images/logo.png"' in conf
    assert 'html_favicon = "logo_favi.ico"' in conf
    assert '"url": "https://github.com/pgmpy/FastCIT"' in conf
    assert '"url": "https://pgmpy.org/"' in conf
    assert '"theme-switcher"' in conf
    for extension in ("myst_parser", "sphinx_copybutton", "sphinx_design", "sphinx.ext.mathjax"):
        assert f'"{extension}"' in conf
    for myst in ("colon_fence", "dollarmath"):
        assert f'"{myst}"' in conf
    for path in ("_static/images/logo.png", "logo_favi.ico", "_static/custom.css"):
        assert (DOCS / path).is_file()
    css = read(STATIC / "custom.css")
    assert "Copied unchanged from pgmpy" in css
    assert "pgmpy Documentation — Custom Styles" in css


@pytest.mark.parametrize("key", TESTS)
def test_copy_button_copies_the_code_of_the_examples(key: str) -> None:
    """sphinx-copybutton copies the lines with a prompt (without the prompt) and the empty lines.

    A code block without a prompt line is copied unchanged.
    """
    conf = read(DOCS / "conf.py")
    assert f'copybutton_prompt_text = r"{COPY_PROMPT}"' in conf
    assert "copybutton_prompt_is_regexp = True" in conf
    prompt = re.compile(rf"^({COPY_PROMPT})(.*)")
    code = []
    for line in read(REPO_ROOT / EXAMPLES["python"].format(key=key)).splitlines():
        if match := prompt.match(line):
            code.append(match[2])
        elif not line.strip():
            code.append(line)
    compile("\n".join(code), key, "exec")  # the transcript without its prompts and output is a script
    for language in ("r", "javascript", "rust"):
        lines = read(REPO_ROOT / EXAMPLES[language].format(key=key)).splitlines()
        assert not any(prompt.match(line) for line in lines), f"{key}, {language}: a line looks like a prompt"


def test_narrow_screens_stack_the_field_list() -> None:
    """At 390 px the theme's grid squeezes the field names of a test page into single letters."""
    css = read(STATIC / "fastcit.css")
    narrow = re.findall(r"@media \(max-width: 40rem\) \{(.*?)\n\}", css, re.S)
    assert any(re.search(r"dl\.field-list \{\s*display: block;", block) for block in narrow)


# ------------------------------------------------------------- benchmark data


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
    assert read(tmp_path / "summary.md") == read(RESULTS / "summary.md")
    assert json.loads(read(tmp_path / "summary.json")) == json.loads(read(RESULTS / "summary.json"))


def check_sweep_is_fresh(results: Path, tmp_path: Path) -> None:
    """sweep.json and sweep.md of `results` must be the output of summarize_sweep.py for its sweep-*.json files."""
    runs = sorted(results.glob("sweep-*.json"))
    assert runs, f"{results} has sweep.json but no sweep-*.json run files"
    for path in runs:
        shutil.copy(path, tmp_path / path.name)
    spec = importlib.util.spec_from_file_location("summarize_sweep", REPO_ROOT / "benchmarks" / "summarize_sweep.py")
    assert spec is not None and spec.loader is not None
    summarize_sweep = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(summarize_sweep)
    summarize_sweep.main(tmp_path)
    assert read(tmp_path / "sweep.json") == read(results / "sweep.json")
    assert read(tmp_path / "sweep.md") == read(results / "sweep.md")
    committed = json.loads(read(results / "sweep.json"))
    assert committed["quick"] is False and not any(m.get("quick") for m in committed["meta"].values()), (
        "the committed sweep comes from a quick run"
    )


@pytest.mark.skipif(not (RESULTS / "sweep.json").exists(), reason="the owner has not committed the full sweep yet")
def test_sweep_json_matches_the_sweep_run_files(tmp_path: Path) -> None:
    check_sweep_is_fresh(RESULTS, tmp_path)


def test_sweep_freshness_check_rejects_a_quick_run(tmp_path: Path) -> None:
    """The check itself: it passes on a full-run folder and fails on quick-run files or a stale sweep.json."""
    fixture = REPO_ROOT / "tests" / "fixtures" / "sweep"
    results, work = tmp_path / "results", tmp_path / "work"
    results.mkdir()
    work.mkdir()
    for path in fixture.glob("*.json"):
        shutil.copy(path, results / path.name)
    sys.path.insert(0, str(REPO_ROOT / "benchmarks"))
    try:
        import summarize_sweep
    finally:
        sys.path.pop(0)
    summarize_sweep.main(results)
    check_sweep_is_fresh(results, work)  # full run: passes
    stale = tmp_path / "stale"
    stale.mkdir()
    (results / "sweep.md").write_text("old\n", encoding="utf-8")
    with pytest.raises(AssertionError):
        check_sweep_is_fresh(results, stale)
    for path in results.glob("sweep-*.json"):  # make the run files quick runs
        data = json.loads(path.read_text(encoding="utf-8"))
        data["meta"]["quick"] = True
        path.write_text(json.dumps(data), encoding="utf-8")
    summarize_sweep.main(results)
    quick = tmp_path / "quick"
    quick.mkdir()
    with pytest.raises(AssertionError, match="quick run"):
        check_sweep_is_fresh(results, quick)


def test_cells_carry_the_run_spread() -> None:
    """Each cell with a result has its run values; a cell gets the mark † exactly when its range exceeds the limit."""
    data = json.loads(read(RESULTS / "summary.json"))
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


# ------------------------------------------------------------------- workflow


def test_docs_workflow_builds_and_publishes_the_site() -> None:
    workflow = yaml.safe_load(read(WORKFLOW))
    # PyYAML reads the bare key `on` as the boolean True.
    paths = workflow[True]["push"]["paths"]
    for path in ("docs/**", "benchmarks/results/**", "README.md"):
        assert path in paths
    for example in EXAMPLES.values():
        assert any(fnmatch(example.format(key="chi_squared"), path) for path in paths), f"{example} is not a trigger"
    steps = workflow["jobs"]["deploy"]["steps"]
    assert steps[0].get("uses", "").startswith("actions/checkout@")
    runs = [step.get("run", "") for step in steps]
    install = next(i for i, run in enumerate(runs) if "pip install -r docs/requirements.txt -c docs/constraints.txt" in run)
    build = next(i for i, run in enumerate(runs) if 'sphinx-build -W -b html -d "$RUNNER_TEMP/doctrees" docs site' in run)
    downloads = {
        step["with"]["path"]: i
        for i, step in enumerate(steps)
        if step.get("uses", "").startswith("actions/download-artifact@")
    }
    assert set(downloads) == {"site/rust/", "site/r/", "site/js/", "site/python/"}
    # The build creates site/; the API sites go into it afterwards.
    assert install < build < min(downloads.values())
    assert "docs/site" not in read(WORKFLOW)
    # The deploy workflow has Pages permissions, so it must not run on pull requests.
    assert "pull_request" not in workflow[True]


def test_docs_check_workflow_builds_the_site_on_pull_requests() -> None:
    workflow = yaml.safe_load(read(CHECK_WORKFLOW))
    paths = workflow[True]["pull_request"]["paths"]
    for path in (
        "docs/**",
        "crates/*/examples/**",
        "crates/ci-r/inst/examples/**",
        "benchmarks/results/**",
        "README.md",
        "tests/test_docs_site.py",
    ):
        assert path in paths
    for example in EXAMPLES.values():
        assert any(fnmatch(example.format(key="chi_squared"), path) for path in paths), f"{example} is not a trigger"
    # Read access only: no Pages or id-token permission on the pull request path.
    assert workflow["permissions"] == {"contents": "read"}
    text = read(CHECK_WORKFLOW)
    for forbidden in ("pages:", "id-token", "deploy-pages", "upload-pages-artifact"):
        assert forbidden not in text
    (job,) = workflow["jobs"].values()
    assert "permissions" not in job
    steps = job["steps"]
    python = next(step for step in steps if step.get("uses", "").startswith("actions/setup-python@"))
    assert python["with"]["python-version"] == "3.13"
    runs = [step.get("run", "") for step in steps]
    install = next(i for i, run in enumerate(runs) if "pip install -r docs/requirements.txt -c docs/constraints.txt" in run)
    build = next(i for i, run in enumerate(runs) if 'sphinx-build -W -b html -d "$RUNNER_TEMP/doctrees" docs site' in run)
    test = next(i for i, run in enumerate(runs) if "pytest tests/test_docs_site.py" in run)
    assert install < build < test
    assert steps[test].get("env", {}).get("FASTCIT_DOCS_REQUIRE_SPHINX") == "1"


# ------------------------------------------------------------ built site (Sphinx)

SPHINX_MODULES = ("sphinx", "myst_parser", "sphinx_design", "pydata_sphinx_theme", "sphinx_copybutton")


def build(out: Path, sweep_json: Path | None = None) -> Path:
    """Build the site with warnings as errors, as the docs workflow does. sweep_json replaces the chart data."""
    for module in SPHINX_MODULES:
        if REQUIRE_SPHINX:
            importlib.import_module(module)  # fail, do not skip
        else:
            pytest.importorskip(module, reason="the Sphinx stack of docs/requirements.txt is not installed")
    env = {key: value for key, value in os.environ.items() if key != "FASTCIT_SWEEP_JSON"}
    if sweep_json is not None:
        env["FASTCIT_SWEEP_JSON"] = str(sweep_json)
    result = subprocess.run(
        [sys.executable, "-m", "sphinx", "-W", "-q", "-b", "html", str(DOCS), str(out)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return out


@pytest.fixture(scope="module")
def site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return build(tmp_path_factory.mktemp("site"))


@pytest.fixture(scope="module")
def sweep_site(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    """A build with chart data, whether or not benchmarks/results/sweep.json exists."""
    data = tmp_path_factory.mktemp("data") / "sweep.json"
    data.write_text('{"source": "tests/test_docs_site.py", "languages": []}\n', encoding="utf-8")
    return build(tmp_path_factory.mktemp("sweep-site"), data), data


def code_blocks(page: str) -> list[str]:
    """Return the text of each highlighted code block of a built page, in page order."""
    blocks = re.findall(r'<div class="highlight"><pre>(.*?)</pre></div>', page, re.S)
    return [html.unescape(re.sub(r"<[^>]+>", "", block)) for block in blocks]


def built_pages(site: Path) -> list[Path]:
    return [path for path in site.rglob("*.html") if "_static" not in path.parts]


def test_build_has_every_page(site: Path) -> None:
    pages = ("index.html", "benchmark.html", "api.html", "tests/index.html", *(f"tests/{key}.html" for key in TESTS))
    for page in pages:
        assert (site / page).is_file(), page


def test_built_navbar_order(site: Path) -> None:
    for page in ("index.html", "benchmark.html", "tests/chi_squared.html"):
        navbar = re.findall(r'<ul class="bd-navbar-elements navbar-nav">(.*?)</ul>', read(site / page), re.S)
        assert navbar, page  # the header and the narrow-screen sidebar
        for items in navbar:
            assert re.findall(r'<a class="nav-link[^"]*"[^>]*>\s*(.*?)\s*</a>', items) == NAVBAR, page


def test_chart_assets_only_on_the_benchmark_page(site: Path) -> None:
    for path in built_pages(site):
        page = read(path)
        expected = path == site / "benchmark.html"
        for asset in ("_static/sweep-chart.js", "_static/sweep-chart.css"):
            assert (asset in page) == expected, f"{path.relative_to(site)}: {asset}"


def test_built_benchmark_page_follows_the_data(site: Path) -> None:
    """With sweep.json the page has the chart and the build copies the file; without it, the page has the notice."""
    page = read(site / "benchmark.html")
    if SWEEP_JSON.exists():
        assert (site / "sweep.json").read_bytes() == SWEEP_JSON.read_bytes()
        assert 'class="sweep-chart"' in page and SWEEP_NOTICE not in page
    else:
        assert not (site / "sweep.json").exists()
        assert 'class="sweep-chart"' not in page and page.count(SWEEP_NOTICE) == 1


def test_built_benchmark_page_with_data(sweep_site: tuple[Path, Path]) -> None:
    site, data = sweep_site
    assert (site / "sweep.json").read_bytes() == data.read_bytes()
    page = read(site / "benchmark.html")
    assert page.count('<div class="sweep-chart" data-src="sweep.json"></div>') == 1
    assert SWEEP_NOTICE not in page
    assert "<noscript>" in page


def test_chart_reads_the_sphinx_design_tab_storage_key(site: Path) -> None:
    """The language control starts on the language that sphinx-design stored: localStorage[<prefix><group>].

    This key is internal to sphinx-design (pinned in docs/requirements.txt). The test fails when a
    new sphinx-design version changes how it stores the selected tab.
    """
    page = read(site / "benchmark.html")
    found = re.findall(r'<script data-sd-tabs-storage-prefix="([^"]*)" src="_static/design-tabs\.js', page)
    assert len(found) == 1, "design-tabs.js no longer receives its storage prefix on the script tag"
    prefix = found[0]
    assert prefix, "sphinx-design does not persist the tab choice (empty prefix)"
    design_tabs = read(site / "_static" / "design-tabs.js")
    assert 'getAttribute("data-sd-tabs-storage-prefix")' in design_tabs
    assert "localStorage.getItem(storageKeyPrefix + group)" in design_tabs
    assert 'getAttribute("data-sync-group")' in design_tabs
    home = read(site / "index.html")
    for language in ("python", "r"):  # the sync ids that the chart's language keys must match
        label = rf'<label [^>]*class="sd-tab-label" data-sync-group="language" data-sync-id="{language}"'
        assert re.search(label, home)
    script = read(site / "_static" / "sweep-chart.js")
    assert f'var DEFAULT_TABS_PREFIX = "{prefix}";' in script
    assert 'var LANGUAGE_GROUP = "language";' in script
    assert 'getAttribute("data-sd-tabs-storage-prefix")' in script
    assert "prefix + LANGUAGE_GROUP" in script


def test_built_home_page_shows_both_runtime_tables(site: Path) -> None:
    page = read(site / "index.html")
    section = re.findall(r'<section id="runtime-comparison">(.*?)</section>', page, re.S)
    assert len(section) == 1
    tables = re.findall(r"<table\b.*?</table>", section[0], re.S)
    assert len(tables) == 2
    assert "pgmpy dev" in tables[0] and "FastCIT (R)" in tables[1]


def test_deploy_checks_only_files_the_site_has(site: Path) -> None:
    """The deploy job fails when a file of its "Check the site" step is missing.

    Each file there must come from the Sphinx build or be one of the API sites that the job adds.
    """
    steps = yaml.safe_load(read(WORKFLOW))["jobs"]["deploy"]["steps"]
    (check,) = [step["run"] for step in steps if step.get("name") == "Check the site"]
    files = re.findall(r"^\s*for file in (.*?); do$", check, re.S | re.M)
    assert len(files) == 1, "the check step must list its files in one for loop"
    for name in files[0].replace("\\", " ").split():
        if name in API_TARGETS:
            continue  # added by the deploy job after the build
        assert (site / name).is_file(), f"the deploy job checks site/{name}, but the build does not write it"


def test_built_home_page_shows_the_quickstart_examples(site: Path) -> None:
    blocks = code_blocks(read(site / "index.html"))
    for language, name in LANGUAGES.items():
        assert read(REPO_ROOT / EXAMPLES[language].format(key="fisher_z")) in blocks
        assert readme_install(name) + "\n" in blocks


@pytest.mark.parametrize("key", TESTS)
def test_built_test_page_shows_each_example_in_a_language_tab(site: Path, key: str) -> None:
    page = read(site / "tests" / f"{key}.html")
    labels = re.findall(r'<label [^>]*class="sd-tab-label" data-sync-group="(\w+)" data-sync-id="(\w+)"', page)
    assert labels == [("language", language) for language in LANGUAGES]
    blocks = code_blocks(page)
    examples = [read(REPO_ROOT / EXAMPLES[language].format(key=key)) for language in LANGUAGES]
    assert [block for block in blocks if block in examples] == examples


def test_built_copy_button_uses_the_doctest_prompts(site: Path) -> None:
    script = read(site / "_static" / "copybutton.js")
    prompt = COPY_PROMPT.replace("\\", "\\\\")
    assert f"formatCopyText(text, '{prompt}', true, true, true, true," in script


def test_built_formulas_use_mathjax(site: Path) -> None:
    for key in ("chi_squared", "fisher_z"):
        page = read(site / "tests" / f"{key}.html")
        assert 'class="math notranslate nohighlight"' in page
        assert "https://cdn.jsdelivr.net/npm/mathjax@" in page


def test_built_internal_links_resolve(site: Path) -> None:
    """Every relative link of a built page points to a file (and an id) of the site."""
    ids: dict[Path, set[str]] = {}
    for path in built_pages(site):
        ids[path.resolve()] = set(re.findall(r'\bid="([^"]+)"', read(path)))
    for path in built_pages(site):
        if path.parts[len(site.parts)] in ("rust", "r", "js", "python"):
            continue
        for link in re.findall(r'\b(?:href|src)="([^"]+)"', read(path)):
            link = html.unescape(link)
            assert not link.startswith("/"), f"{path.name}: {link} breaks under the /FastCIT/ sub-path"
            if re.match(r"^[a-z][a-z0-9+.-]*:", link) or link.startswith("//"):
                continue
            target, _, fragment = link.partition("#")
            target = target.split("?")[0]
            resolved = (path.parent / target).resolve() if target else path.resolve()
            relative = resolved.relative_to(site.resolve()).as_posix()
            if relative in API_TARGETS:
                continue  # added by the deploy job
            assert resolved.exists(), f"{path.relative_to(site)}: {link} does not resolve"
            if fragment and resolved.suffix == ".html":
                assert fragment in ids[resolved], f"{path.relative_to(site)}: #{fragment} is not in {relative}"


def test_built_pages_have_no_unexpected_external_urls(site: Path) -> None:
    for path in built_pages(site):
        page = read(path)
        for url in re.findall(r'\b(?:href|src)="(https?://[^"]+)"', page):
            assert url.startswith(ALLOWED_EXTERNAL), f"{path.relative_to(site)}: unexpected external URL {url}"
