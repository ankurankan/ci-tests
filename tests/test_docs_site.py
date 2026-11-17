"""Checks for the documentation site in docs/ (Sphinx, MyST pages), published at https://pgmpy.org/FastCIT/.

The home page repeats the install commands and the quickstart examples of the README. These tests
fail when the two copies differ. The home page includes the two tables of median call times from
benchmarks/results/summary.md. Each test page must show the CI-run example file of each language
in a synced language tab set. The tests also check the benchmark summary and the docs workflow.

The tests at the end build the site with Sphinx. They skip when the Sphinx stack of
docs/requirements.txt is not installed (for example in the golden-fixture job of python.yml).
"""

from __future__ import annotations

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
TEST_PAGES = DOCS / "tests"
STATIC = DOCS / "_static"
README = REPO_ROOT / "README.md"
RESULTS = REPO_ROOT / "benchmarks" / "results"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "docs.yml"
CHECK_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "docs-check.yml"
# Set in docs-check.yml: there the Sphinx tests must run, not skip.
REQUIRE_SPHINX = os.environ.get("FASTCIT_DOCS_REQUIRE_SPHINX") == "1"

LANGUAGES = {"python": "Python", "r": "R", "javascript": "JavaScript", "rust": "Rust"}
EXAMPLES = {
    "python": "crates/ci-python/examples/{key}.py",
    "r": "crates/ci-r/inst/examples/tests/{key}.R",
    "javascript": "crates/ci-js/examples/{key}.js",
    "rust": "crates/ci-core/examples/{key}.rs",
}
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
def test_quickstart_example_matches_readme(language: str) -> None:
    items = {key: body for _, key, body in tab_items(section(read(INDEX), "Quickstart"))}
    assert fenced_code(items[language]) == readme_example(LANGUAGES[language])


@pytest.mark.parametrize("language", LANGUAGES)
def test_install_command_matches_readme(language: str) -> None:
    items = {key: body for _, key, body in tab_items(section(read(INDEX), "Install"))}
    assert fenced_code(items[language]) == readme_install(LANGUAGES[language])


@pytest.mark.parametrize("heading", ["Install", "Quickstart"])
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
    assert re.match(r"\s*# .+\n\n:Data types: .+\n\n## Usage\n", body), "the data types must lead the page"
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
        assert includes == [(f"../../{example}", language)], f"{key}, {language}: include {example}"
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


@pytest.fixture(scope="module")
def site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the site with warnings as errors, as the docs workflow does."""
    for module in SPHINX_MODULES:
        if REQUIRE_SPHINX:
            importlib.import_module(module)  # fail, do not skip
        else:
            pytest.importorskip(module, reason="the Sphinx stack of docs/requirements.txt is not installed")
    out = tmp_path_factory.mktemp("site")
    result = subprocess.run(
        [sys.executable, "-m", "sphinx", "-W", "-q", "-b", "html", str(DOCS), str(out)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return out


def code_blocks(page: str) -> list[str]:
    """Return the text of each highlighted code block of a built page, in page order."""
    blocks = re.findall(r'<div class="highlight"><pre>(.*?)</pre></div>', page, re.S)
    return [html.unescape(re.sub(r"<[^>]+>", "", block)) for block in blocks]


def built_pages(site: Path) -> list[Path]:
    return [path for path in site.rglob("*.html") if "_static" not in path.parts]


def test_build_has_every_page(site: Path) -> None:
    for page in ("index.html", "api.html", "tests/index.html", *(f"tests/{key}.html" for key in TESTS)):
        assert (site / page).is_file(), page


def test_built_home_page_shows_both_runtime_tables(site: Path) -> None:
    page = read(site / "index.html")
    section = re.findall(r'<section id="runtime-comparison">(.*?)</section>', page, re.S)
    assert len(section) == 1
    tables = re.findall(r"<table\b.*?</table>", section[0], re.S)
    assert len(tables) == 2
    assert "pgmpy dev" in tables[0] and "FastCIT (R)" in tables[1]


def test_built_home_page_shows_the_readme_examples(site: Path) -> None:
    blocks = code_blocks(read(site / "index.html"))
    for name in LANGUAGES.values():
        assert readme_example(name) + "\n" in blocks
        assert readme_install(name) + "\n" in blocks


@pytest.mark.parametrize("key", TESTS)
def test_built_test_page_shows_each_example_in_a_language_tab(site: Path, key: str) -> None:
    page = read(site / "tests" / f"{key}.html")
    labels = re.findall(r'<label [^>]*class="sd-tab-label" data-sync-group="(\w+)" data-sync-id="(\w+)"', page)
    assert labels == [("language", language) for language in LANGUAGES]
    blocks = code_blocks(page)
    examples = [read(REPO_ROOT / EXAMPLES[language].format(key=key)) for language in LANGUAGES]
    assert [block for block in blocks if block in examples] == examples


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
