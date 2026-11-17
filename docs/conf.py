"""Sphinx configuration for the FastCIT documentation (https://pgmpy.org/FastCIT/).

The theme set-up follows pgmpy's docs/conf.py (https://github.com/pgmpy/pgmpy/blob/dev/docs/conf.py):
pydata-sphinx-theme with the same options, the pgmpy logo, pgmpy's custom.css, MyST Markdown,
sphinx-design and sphinx-copybutton. The pgmpy-only parts (version switcher, ads, analytics,
API autodoc, bibtex, notebooks) are not used here.

Build: sphinx-build -W -b html docs site
"""

from __future__ import annotations

import shutil
from pathlib import Path

DOCS = Path(__file__).resolve().parent
REPO_ROOT = DOCS.parent
# The home page chart reads this file as benchmarks.json, next to index.html.
BENCHMARK_SUMMARY = REPO_ROOT / "benchmarks" / "results" / "summary.json"

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


# -- The runtime chart on the home page ------------------------------------


def _add_chart_assets(app, pagename, templatename, context, doctree):
    """Load the chart script and styles on the home page only."""
    if pagename == root_doc:
        app.add_css_file("benchmark-chart.css")
        app.add_js_file("benchmark-chart.js", loading_method="defer")


def _copy_benchmark_data(app, exception):
    """Copy benchmarks/results/summary.json to <output>/benchmarks.json."""
    if exception is None and app.builder.format == "html":
        shutil.copyfile(BENCHMARK_SUMMARY, Path(app.outdir) / "benchmarks.json")


def setup(app):
    app.connect("html-page-context", _add_chart_assets)
    app.connect("build-finished", _copy_benchmark_data)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
