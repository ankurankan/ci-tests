"""Sphinx configuration for the FastCIT documentation (https://pgmpy.org/FastCIT/).

The theme set-up follows pgmpy's docs/conf.py (https://github.com/pgmpy/pgmpy/blob/dev/docs/conf.py):
pydata-sphinx-theme with the same options, the pgmpy logo, pgmpy's custom.css, MyST Markdown,
sphinx-design and sphinx-copybutton. The pgmpy-only parts (version switcher, ads, analytics,
API autodoc, bibtex, notebooks) are not used here.

Build: sphinx-build -W -b html docs site
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

# -- General configuration ------------------------------------------------

extensions = [
    "sphinx.ext.mathjax",
    "myst_parser",
    "sphinx_copybutton",
    "sphinx_design",
]

source_suffix = {".md": "markdown"}
root_doc = "index"

project = "FastCIT"
copyright = "2026, pgmpy"
author = "pgmpy"
language = "en"

# _includes holds Markdown fragments that other pages include.
exclude_patterns = ["_build", "_includes", "Thumbs.db", ".DS_Store"]
pygments_style = "tango"

myst_enable_extensions = ["colon_fence", "deflist", "fieldlist", "dollarmath"]
myst_heading_anchors = 3

# The Python examples are doctest transcripts. The copy button copies only the code lines,
# without the prompts. A code block without prompts (R, JavaScript, Rust) is copied unchanged.
copybutton_prompt_text = r">>> |\.\.\. "
copybutton_prompt_is_regexp = True

# -- Options for HTML output ----------------------------------------------

html_theme = "pydata_sphinx_theme"

html_title = "FastCIT"
html_favicon = "logo_favi.ico"
html_logo = "_static/images/logo.png"
html_static_path = ["_static"]
html_sidebars = {
    "**": ["sidebar-nav-bs.html"],
    "index": [],
    "api": [],  # no child pages, so the section navigation would be empty
    "benchmark": [],
}

html_theme_options = {
    "logo": {
        "text": "FastCIT",
    },
    "navbar_start": ["navbar-logo"],
    "navbar_center": ["navbar-nav"],
    "navbar_end": ["theme-switcher", "navbar-icon-links"],
    "navbar_persistent": ["search-button-field"],
    "header_links_before_dropdown": 4,
    "collapse_navigation": True,
    "navigation_depth": 4,
    "show_nav_level": 1,
    "show_toc_level": 2,
    "secondary_sidebar_items": {
        "**": ["page-toc"],
        "index": [],
        "benchmark": [],  # the chart gets the full width
    },
    "primary_sidebar_end": [],
    "footer_start": ["copyright"],
    "footer_center": [],
    "footer_end": [],
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/pgmpy/FastCIT",
            "icon": "fa-brands fa-github",
        },
        {
            "name": "pgmpy.org",
            "url": "https://pgmpy.org/",
            "icon": "_static/images/logo.png",
            "type": "local",
        },
    ],
}

html_css_files = ["custom.css", "fastcit.css"]
# Without a default, the theme reads an empty mode on a first visit and logs a console error.
html_context = {"default_mode": "auto"}

# MathJax as in pgmpy (the Sphinx default), plus hidden MathML for screen readers.
mathjax4_config = {"options": {"menuOptions": {"settings": {"assistiveMml": True}}}}

html_search_language = "en"
htmlhelp_basename = "fastcitdoc"


# -- The chart on the Benchmark page ----------------------------------------

# benchmarks/summarize_sweep.py writes the chart data. Without the file, docs/benchmark.md shows a notice
# instead of the chart. The tests set FASTCIT_SWEEP_JSON to build the page with other data.
SWEEP_JSON = Path(os.environ.get("FASTCIT_SWEEP_JSON") or Path(__file__).parents[1] / "benchmarks/results/sweep.json")
if SWEEP_JSON.is_file():
    tags.add("sweep")  # noqa: F821 (Sphinx gives conf.py the build tags)


def _add_chart_assets(app, pagename, templatename, context, doctree):
    """Load the chart script and styles on the Benchmark page only."""
    if pagename == "benchmark":
        app.add_css_file("sweep-chart.css")
        app.add_js_file("sweep-chart.js", loading_method="defer")


def _copy_sweep_data(app, exception):
    """Copy the chart data to <output>/sweep.json, next to benchmark.html."""
    if exception is None and app.builder.format == "html" and SWEEP_JSON.is_file():
        shutil.copyfile(SWEEP_JSON, Path(app.outdir) / "sweep.json")


def setup(app):
    app.connect("html-page-context", _add_chart_assets)
    app.connect("build-finished", _copy_sweep_data)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
