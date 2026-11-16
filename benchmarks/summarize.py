"""Write summary.md and summary.json from the run files of the benchmark.

Usage: python benchmarks/summarize.py DIR

DIR holds the run files: python-1.json, python-2.json, ... (main Python interpreter), r-1.json, r-2.json, ...
(R), and optional extra Python groups such as python-dowhy-1.json, python-dowhy-2.json, ... Each extra group comes
from another interpreter and adds its engines to the Python tables (dowhy runs under Python 3.11, because it does
not support Python 3.14). An engine of an extra group that the main group also has (FastCIT) is a reference in
the same interpreter. The summary records it with the run details, not as a table column.

The runs of one group are independent runs in new processes. Each cell gives the median of the run values and
the range (smallest and largest run value). A cell whose range is more than 25 % of its median gets the mark †.
The script writes DIR/summary.md and DIR/summary.json. Both files come from the same tables. The documentation
home page reads summary.json.
"""
import json
import math
import re
import statistics
import sys
from pathlib import Path

PY_ROWS = ["chi_square", "g_sq", "cressie_read", "freeman_tukey", "modified_ll", "fisher_z", "pearson_t", "hsic",
           "kci_300", "kci_1000", "gcm", "pillai"]
PY_COLS = [("fastcit", "FastCIT"), ("pgmpy", "pgmpy dev"), ("causal-learn", "causal-learn"), ("gcastle", "gcastle"),
           ("tigramite", "tigramite"), ("pingouin", "pingouin"), ("hyppo", "hyppo"), ("dowhy", "dowhy")]
R_ROWS = ["chi_square", "g_sq", "fisher_z", "pearson_t", "hsic", "gcm"]
R_COLS = [("fastcit", "FastCIT (R)"), ("pcalg", "pcalg"), ("bnlearn", "bnlearn"), ("dHSIC", "dHSIC"),
          ("Rfast", "Rfast"), ("ppcor", "ppcor"), ("comets", "comets")]
PY_LABELS = {"chi_square": "χ²", "g_sq": "G²", "cressie_read": "Cressie-Read", "freeman_tukey": "Freeman-Tukey",
             "modified_ll": "Modified log-likelihood", "fisher_z": "Fisher-z", "pearson_t": "Pearson t",
             "hsic": "HSIC (n = 300)", "kci_300": "KCI (n = 300)", "kci_1000": "KCI (n = 1 000)", "gcm": "GCM",
             "pillai": "Pillai"}
R_LABELS = {**PY_LABELS, "hsic": "HSIC (median width)"}
# Rows where pgmpy and gcastle apply the Yates correction. Both engines are compared with FastCIT with Yates on.
YATES_ROWS = ("chi_square", "g_sq", "cressie_read", "freeman_tukey", "modified_ll")
YATES_ENGINES = ("pgmpy", "gcastle")

# Marks on cells and rows. The text of each mark is printed under the table.
PY_MARKS = {("pillai", "pgmpy"): "ᵃ",
            **{(row, name): "ᵇ" for row in ("chi_square", "g_sq", "cressie_read", "freeman_tukey", "modified_ll")
               for name in ("pgmpy", "gcastle")},
            ("hsic", "causal-learn"): "ᶜ", ("hsic", "hyppo"): "ᶜ", ("kci_300", "causal-learn"): "ᶜ"}
PY_ROW_MARKS = {"fisher_z": "ᵈ", "pearson_t": "ᵈ"}
R_MARKS = {("g_sq", "pcalg"): "ᵉ", ("chi_square", "bnlearn"): "ᵉᶠ", ("g_sq", "bnlearn"): "ᵉᶠ",
           ("fisher_z", "bnlearn"): "ᶠ", ("pearson_t", "bnlearn"): "ᶠ", ("hsic", "dHSIC"): "ᶜ",
           ("chi_square", "Rfast"): "ᵉ", ("g_sq", "Rfast"): "ᵉ", ("pearson_t", "ppcor"): "ᵍ"}
R_ROW_MARKS = {"fisher_z": "ᵈ", "pearson_t": "ᵈ"}
FOOT = {
    "ᵃ": "pgmpy runs a random-forest Pillai test. FastCIT runs a linear Pillai test. The two tests differ.",
    "ᵇ": ("pgmpy and gcastle apply the Yates correction on 2 × 2 tables and cannot turn it off. "
          "FastCIT runs without it."),
    "ᶜ": "Different null approximation or kernel width rule from FastCIT.",
    "ᵉ": "Uses the nominal degrees of freedom. FastCIT uses the adjusted degrees of freedom.",
    "ᶠ": ("bnlearn ci.test() checks the whole data frame in each call. "
          "The benchmark gives it only the columns of the query."),
    "ᵍ": ("ppcor needs at least one conditioning variable. "
          "For a query with an empty set, the benchmark calls stats::cor.test, which runs the same t-test."),
}
# The footnote of the setup mark differs for each table, because each table has its own packages.
FOOT_E = {
    "python": ("The time does not include the one-time setup. FastCIT and causal-learn precompute "
               "the correlation matrix. FastCIT computes it in the first call and keeps it. "
               "The other packages in these rows compute it in every call. See the total-time tables."),
    "r": ("The time does not include the one-time setup. FastCIT and pcalg precompute the correlation matrix. "
          "FastCIT computes it in the first call and keeps it. bnlearn and ppcor compute it in every call. "
          "See the total-time tables."),
}
MARK_ORDER = "ᵃᵇᶜᵈᵉᶠᵍ*†"
STAR_TABLE = ("The engine raised an error or returned NaN on some queries. See the lists below. "
              "The median uses only the queries with a result. "
              "Those queries can cost less or more than the excluded ones. "
              "Compare such a cell with care.")
STAR_TOTAL = ("The engine raised an error or returned NaN on some queries. "
              "The total includes the time of those queries.")
SPREAD_LIMIT = 0.25  # a cell whose run range is more than this share of its median gets the mark †
SPREAD = ("The largest and smallest of the {runs} run {what} differ by more than 25 % of the cell value. "
          "Compare such a cell with care.")
PY_TOTAL_NOTE = ("Each pass builds the state of the engine (data conversion, test object, correlation matrix). "
                 "Then it runs all queries of the group once. Each run keeps its fastest of {passes} passes. "
                 "The table shows the median of the {runs} run values.")
R_TOTAL_NOTE = ("Each run keeps its fastest of {passes} passes. The table shows the median of the {runs} run values. "
                "bnlearn, dHSIC, ppcor and comets have no setup.")
RUN_GROUP = re.compile(r"^(python|r)(-.+)?\.json$")  # the files that hold runs
RUN_FILE = re.compile(r"^(?P<group>.+)-(?P<run>\d+)\.json$")
# Meta fields that must be the same in every run of a group. The other fields belong to one run.
COMMON = ("cpu", "logical_cpus", "os", "python", "r", "engines", "rows", "quick", "passes", "versions", "helpers",
          "commits", "fastcit_trees", "threads", "affinity")
PER_RUN = ("date", "seed", "uptime_start", "uptime_end", "power", "power_end", "harness_floor_ms")


def fmt(ms):
    if ms is None or (isinstance(ms, float) and math.isnan(ms)):
        return "—"
    if ms >= 100:
        return f"{ms:,.0f}".replace(",", " ")
    if ms >= 10:
        return f"{ms:.1f}"
    if ms >= 1:
        return f"{ms:.2f}"
    return f"{ms:.3f}"


def spread(values):
    """Return the median, smallest and largest run value and the range as a share of the median."""
    vals = [v for v in values if good(v)]
    if not vals:
        return None, None, None, None
    mid = statistics.median(vals)
    return mid, min(vals), max(vals), (max(vals) - min(vals)) / mid if mid > 0 else None


def table_data(results, rows, cols, labels, marks, row_marks, key="median_ms"):
    """Return one table as data: ordered columns, and ordered rows with one cell per column.

    A cell holds the median of the run values in ms (None if there is no result), the text that summary.md prints,
    its marks, the run values and their range. Cell marks appear in both tables. Row marks appear only in the
    median tables. "*" marks an engine with errors or NaN. "†" marks a cell whose run range is more than 25 % of
    its median.
    """
    per_call = key == "median_ms"
    out = []
    for r in rows:
        eng = results.get(r, {}).get("engines", {})
        cells = []
        for name, _ in cols:
            v = eng.get(name)
            if not v:
                cells.append({"value": None, "text": "—", "marks": []})
                continue
            runs = v[key + "_runs"]
            mid, lo, hi, rel = spread(runs)
            flagged = rel is not None and rel > SPREAD_LIMIT
            cell_marks = list(marks.get((r, name), ""))
            if v["errors"] or v["nan"]:
                cell_marks.append("*")
            if flagged:
                cell_marks.append("†")
            cells.append({"value": mid, "text": fmt(mid), "marks": cell_marks,
                          "errors": v["errors"], "nan": v["nan"], "queries": v["n_queries"],
                          "runs": runs, "min": lo, "max": hi, "range_text": range_text(lo, hi), "spread": rel,
                          "flagged": flagged})
        out.append({"key": r, "label": labels[r], "marks": list(row_marks.get(r, "")) if per_call else [],
                    "cells": cells})
    return {"columns": [{"key": k, "label": label} for k, label in cols], "rows": out}


def table(t):
    out = "| Test | " + " | ".join(c["label"] for c in t["columns"]) + " |\n|---|" + "---:|" * len(t["columns"]) + "\n"
    for row in t["rows"]:
        cells = [c["text"] + "".join(c["marks"]) for c in row["cells"]]
        out += f"| {row['label']}{''.join(row['marks'])} | " + " | ".join(cells) + " |\n"
    return out


def range_text(lo, hi):
    return f"{fmt(lo)}–{fmt(hi)}" if good(lo) and good(hi) else "—"


def range_table(t):
    """The smallest and largest run value of each cell, with † on a flagged cell."""
    out = "| Test | " + " | ".join(c["label"] for c in t["columns"]) + " |\n|---|" + "---:|" * len(t["columns"]) + "\n"
    for row in t["rows"]:
        cells = [c["range_text"] + ("†" if c["flagged"] else "") if c.get("min") is not None else "—"
                 for c in row["cells"]]
        out += f"| {row['label']} | " + " | ".join(cells) + " |\n"
    return out


def flagged_list(eco):
    out = []
    for t in (eco["per_call"], eco["total_per_pass"]):
        for row in t["rows"]:
            for col, c in zip(t["columns"], row["cells"]):
                if c.get("flagged"):
                    out.append(f"- {t['title']}, {row['label']}, {col['label']}: {c['text']} ms, runs "
                               f"{c['range_text']} ms, range {100 * c['spread']:.0f} % of the median")
    return out


def footnote_data(table, foot_d, star, spread_note):
    """Return the notes of every mark that the table uses, in mark order."""
    used = {m for row in table["rows"] for m in row["marks"]}
    used |= {m for row in table["rows"] for cell in row["cells"] for m in cell["marks"]}
    texts = {**FOOT, "ᵈ": foot_d, "*": star, "†": spread_note}
    return [{"mark": m, "text": texts[m]} for m in sorted(used, key=MARK_ORDER.index)]


def footnotes(notes):
    lines = [("\\*" if n["mark"] == "*" else n["mark"]) + " " + n["text"] for n in notes]
    return "\n" + "\n".join(lines) + "\n" if lines else ""


def good(x):
    return x is not None and not (isinstance(x, float) and math.isnan(x))


def maxdiff(a, b):
    d = [abs(x - y) for x, y in zip(a, b) if good(x) and good(y)]
    return max(d) if d else None


def agreement(results, rivals, expected, labels):
    rows = []
    for test, res in results.items():
        eng = res["engines"]
        for name in rivals:
            if name not in eng:
                continue
            base = eng["fastcit"]["p"]
            note = expected.get((test, name), "")
            if test in YATES_ROWS and name in YATES_ENGINES:
                base = eng["fastcit (yates)"]["p"]
                note = f"compared with FastCIT with Yates on ({name} cannot turn it off)"
            n_ok = sum(1 for x, y in zip(base, eng[name]["p"]) if good(x) and good(y))
            rows.append((labels[test], name, maxdiff(base, eng[name]["p"]), n_ok, eng[name]["errors"], eng[name]["nan"], note))
    return rows


def agreement_table(title, rows):
    out = (f"\n{title}\n\n| Test | Package | Largest abs. difference in p-value | Queries compared | Errors | NaN | Note |\n"
           "|---|---|---:|---:|---:|---:|---|\n")
    for label, name, d, n_ok, errs, nan, note in rows:
        out += f"| {label} | {name} | {'—' if d is None else f'{d:.2e}'} | {n_ok} | {errs} | {nan} | {note} |\n"
    return out


def failed_list(results):
    out = []
    for test, res in results.items():
        for name, v in res["engines"].items():
            if v["errors"] or v["nan"]:
                out.append(f"- {res['label']}, {name}: {v['errors']} errors, {v['nan']} NaN of {v['n_queries']} queries")
    return out


def file_name(path):
    return str(path).replace("\\", "/").rsplit("/", 1)[-1]


def power_text(p):
    if not p:
        return "not recorded"
    return (f"AC online {p.get('ac_online', 'unknown')}, profile {p.get('profile', 'unknown')}, "
            f"CPU 0 governor {p.get('governor', 'unknown')}, EPP {p.get('epp', 'unknown')}")


def ms_text(ms):
    return f"{fmt(ms)} ms" if good(ms) else "—"


def meta_block(title, m):
    runtime = f", Python {m['python']}" if m.get("python") else (f", {m['r']}" if m.get("r") else "")
    scope = ""
    if m.get("only"):
        scope = f" (engines {', '.join(m['engines'])}" + (f"; rows {', '.join(m['rows'])}" if m.get("rows") else "") + ")"
    lines = [f"- {title}{scope}: {len(m['runs'])} runs, {m['cpu']} ({m['logical_cpus']} logical CPUs), {m['os']}{runtime}"]
    commits = m.get("commits", {})
    lines.append("  - versions: " + ", ".join(
        f"{k} {v} (dev {commits['pgmpy']})" if k == "pgmpy" and commits.get("pgmpy") else f"{k} {v}"
        for k, v in m["versions"].items()))
    if commits:
        lines.append("  - commits: " + ", ".join(f"{k} {v}" for k, v in commits.items()))
    if m.get("fastcit_trees"):
        lines.append("  - FastCIT code (git tree hashes, check with `git rev-parse <commit>:<path>`): "
                     + ", ".join(f"{k} {v}" for k, v in m["fastcit_trees"].items()))
    if m.get("helpers"):
        lines.append("  - helper packages: " + ", ".join(f"{k} {v}" for k, v in m["helpers"].items()))
    seeds = ", ".join(str(run.get("seed", "unknown")) for run in m["runs"])
    lines.append(f"  - passes: {m['passes']} per run; each pass runs the engines of a row in a new random order "
                 f"(seeds {seeds})")
    aff = m.get("affinity")
    if aff:
        lines.append("  - CPU affinity: " + "; ".join(f"{k} {v}" for k, v in aff.items()))
    else:
        lines.append("  - CPU affinity: not recorded")
    t = m.get("threads", {})
    lines.append(f"  - threads: FastCIT {t.get('fastcit', 'unknown')}; environment variables: {t.get('env') or 'none set'}")
    if t.get("pools"):
        lines.append("  - pools: " + "; ".join(str(x) for x in t["pools"]))
    for k in ("blas", "lapack"):
        if t.get(k):
            lines.append(f"  - {k}: {file_name(t[k])}")
    for row, engines in (m.get("reference") or {}).items():
        for name, v in engines.items():
            lines.append(f"  - same-interpreter reference (not a table column): {v['label']}, {v['package']} "
                         f"{ms_text(v['median_ms'])} per call (runs {v['range_text']} ms)")
    for k, run in enumerate(m["runs"], 1):
        lines.append(f"  - run {k} ({run['file']}): {run.get('date', 'not recorded')}")
        power = power_text(run.get("power"))
        if run.get("power_end") and run["power_end"] != run.get("power"):
            power += f"; at the end: {power_text(run['power_end'])}"
        lines.append(f"    - power: {power}")
        floor = run.get("harness_floor_ms")
        lines.append("    - harness floor (median time of a no-op call, not subtracted): "
                     + (f"{floor:.5f} ms" if good(floor) else "not recorded"))
        lines.append(f"    - uptime before: `{run['uptime_start']}`")
        lines.append(f"    - uptime after: `{run['uptime_end']}`")
    return "\n".join(lines)


def load_groups(d):
    """Return {group: [run data, ...]} for the run files in DIR, each group in run order."""
    groups = {}
    for path in sorted(d.glob("*.json")):
        if not RUN_GROUP.match(path.name):
            continue  # summary.json, queries.json
        m = RUN_FILE.match(path.name)
        group, number = (m["group"], int(m["run"])) if m else (path.stem, 0)
        data = json.loads(path.read_text())
        data["meta"]["file"] = path.name
        groups.setdefault(group, []).append((number, data))
    return {g: [data for _, data in sorted(runs, key=lambda x: x[0])] for g, runs in groups.items()}


def merge_runs(group, runs):
    """Merge the runs of one group into one result set.

    Each engine gets the run values of its median and total (median_ms_runs, total_ms_runs) and their median.
    The p-values and statistics come from the first run. Errors and NaN are the largest count of any run.
    """
    for run in runs:  # the load order of the thread pools changes between processes
        pools = run["meta"].get("threads", {}).get("pools")
        if pools:
            run["meta"]["threads"]["pools"] = sorted(pools)
    first = runs[0]["meta"]
    meta = {k: first[k] for k in COMMON if k in first}
    for run in runs[1:]:
        for k in COMMON:
            if run["meta"].get(k) != first.get(k):
                sys.exit(f"{group}: {k} differs between {first['file']} and {run['meta']['file']}")
    meta["date"] = first["date"]
    meta["runs"] = [{"file": run["meta"]["file"],
                     **{k: run["meta"][k] for k in PER_RUN if k in run["meta"]}} for run in runs]
    for run in meta["runs"]:
        run["uptime_start"] = run["uptime_start"].strip()
        run["uptime_end"] = run["uptime_end"].strip()
    results = {}
    for row, res in runs[0]["results"].items():
        results[row] = {"label": res["label"], "engines": {}}
        for name, v in res["engines"].items():
            try:
                all_runs = [run["results"][row]["engines"][name] for run in runs]
            except KeyError:
                sys.exit(f"{group}: {row} {name} is missing in a run")
            merged = {k: v[k] for k in ("n_queries", "p", "stat") if k in v}
            for key in ("median_ms", "total_ms"):
                vals = [x[key] if good(x[key]) else None for x in all_runs]
                merged[key + "_runs"] = vals
                merged[key] = spread(vals)[0]
            merged["errors"] = max(x["errors"] for x in all_runs)
            merged["nan"] = max(x["nan"] for x in all_runs)
            if "note" in v:
                merged["note"] = v["note"]
            results[row]["engines"][name] = merged
    return {"meta": meta, "results": results}


def load_python(groups):
    """Return the main Python group merged with every extra Python group (python-NAME-k.json).

    An extra group adds its engines to the rows of the main group. An engine that the main group also has
    (FastCIT in the dowhy run) does not replace the main value. It goes to meta["reference"] of the extra group.
    The versions of an extra group stay in its own meta, in meta["other_runs"].
    """
    data = merge_runs("python", groups["python"])
    others = []
    for name in sorted(g for g in groups if g.startswith("python-")):
        extra = merge_runs(name, groups[name])
        reference = {}
        for row, res in extra["results"].items():
            target = data["results"].setdefault(row, {"label": res["label"], "engines": {}})["engines"]
            for eng, v in res["engines"].items():
                if eng in target:
                    mid, lo, hi, _ = spread(v["median_ms_runs"])
                    reference.setdefault(row, {})[eng] = {"label": PY_LABELS.get(row, res["label"]),
                                                          "package": dict(PY_COLS).get(eng, eng),
                                                          "median_ms": mid, "text": fmt(mid), "min": lo, "max": hi,
                                                          "range_text": range_text(lo, hi),
                                                          "runs": v["median_ms_runs"]}
                else:
                    target[eng] = v
        others.append({**extra["meta"], "group": name, "only": True, "reference": reference})
    data["meta"]["other_runs"] = others
    return data


def ecosystem(key, label, data, failed, rows, cols, labels, marks, row_marks, foot_d, total_note):
    """Return the summary.json part of one ecosystem: its run meta and its two tables."""
    meta = data["meta"]
    runs = len(meta["runs"])
    per_call = table_data(data["results"], rows, cols, labels, marks, row_marks)
    total = table_data(data["results"], rows, cols, labels, marks, {}, key="total_ms")
    eco = {
        "key": key, "label": label, "meta": meta,
        "spread": {"limit": SPREAD_LIMIT, "runs": runs},
        "per_call": {"title": f"{label}, median time of one call", **per_call},
        "total_per_pass": {"title": f"{label}, total time of one pass",
                           "note": total_note.format(passes=meta["passes"], runs=runs), **total},
    }
    eco["per_call"]["footnotes"] = footnote_data(eco["per_call"], foot_d, STAR_TABLE,
                                                 SPREAD.format(runs=runs, what="medians"))
    eco["total_per_pass"]["footnotes"] = footnote_data(eco["total_per_pass"], foot_d, STAR_TOTAL,
                                                       SPREAD.format(runs=runs, what="totals"))
    eco["spread"]["flagged"] = flagged_list(eco)
    return eco


def main(d):
    d = Path(d)
    groups = load_groups(d)
    py = load_python(groups)
    r = merge_runs("r", groups["r"])
    quick = py["meta"].get("quick") or r["meta"].get("quick") or any(m.get("quick") for m in py["meta"]["other_runs"])
    failed = failed_list(py["results"])
    failed_r = failed_list(r["results"])
    eco_py = ecosystem("python", "Python packages", py, failed, PY_ROWS, PY_COLS, PY_LABELS, PY_MARKS, PY_ROW_MARKS,
                       FOOT_E["python"], PY_TOTAL_NOTE)
    eco_r = ecosystem("r", "R packages", r, failed_r, R_ROWS, R_COLS, R_LABELS, R_MARKS, R_ROW_MARKS,
                      FOOT_E["r"], R_TOTAL_NOTE)
    runs = sorted({len(py["meta"]["runs"]), len(r["meta"]["runs"])})
    out = "# FastCIT benchmark summary\n\n"
    out += ("The first two tables give the median time of one test call, in milliseconds. "
            "The next two tables give the total time of one pass, in milliseconds. Lower is better.\n\n")
    out += (f"Each language ran {' or '.join(map(str, runs))} times, each time in a new process. "
            "A cell gives the median of the run values. "
            "The spread tables give the smallest and largest run value of each cell. "
            "† marks a cell whose run values differ by more than 25 % of the cell value.\n\n")
    out += "## Setup\n\n" + "\n".join([meta_block("Python run", py["meta"])] + [meta_block("Python run", m) for m in py["meta"]["other_runs"]]
                                      + [meta_block("R run", r["meta"])]) + "\n"
    out += "\nQuick run (2 queries per group): " + ("yes" if quick else "no") + "\n"
    for eco in (eco_py, eco_r):
        out += f"\n## {eco['per_call']['title']}\n\n" + table(eco["per_call"]) + footnotes(eco["per_call"]["footnotes"])
    for eco in (eco_py, eco_r):
        t = eco["total_per_pass"]
        out += f"\n## {t['title']}\n\n{t['note']}\n\n" + table(t) + footnotes(t["footnotes"])
    out += "\n## Spread across runs\n\nEach cell gives the smallest and the largest run value, in milliseconds.\n"
    for eco in (eco_py, eco_r):
        for t in (eco["per_call"], eco["total_per_pass"]):
            out += f"\n### {t['title']}, range of the run values\n\n" + range_table(t)
    flagged = eco_py["spread"]["flagged"] + eco_r["spread"]["flagged"]
    out += ("\nCells whose run values differ by more than 25 % of the cell value:\n\n" + "\n".join(flagged) + "\n"
            if flagged else "\nNo cell has run values that differ by more than 25 % of the cell value.\n")
    if failed or failed_r:
        out += "\n## Errors and NaN\n\n" + "\n".join(["Python:"] * bool(failed) + failed + ["R:"] * bool(failed_r) + failed_r) + "\n"
    else:
        out += "\n## Errors and NaN\n\nNo engine raised an error or returned NaN.\n"
    py_exp = {("pillai", "pgmpy"): "random forest, different test",
              ("hsic", "causal-learn"): "unconditional kci; kernel width or null approximation differs",
              ("hsic", "hyppo"): "chi-squared null approximation, not gamma",
              ("kci_300", "causal-learn"): "kernel width or null approximation differs"}
    out += agreement_table("## Agreement, Python packages", agreement(
        py["results"], [k for k, _ in PY_COLS[1:]], py_exp, PY_LABELS))
    r_exp = {("chi_square", "bnlearn"): "default x2 uses nominal dof (see the adf row)",
             ("g_sq", "bnlearn"): "default mi uses nominal dof (see the adf row)",
             ("g_sq", "pcalg"): "nominal dof (adaptDF = FALSE)",
             ("hsic", "dHSIC"): "different kernel width or null approximation",
             ("chi_square", "Rfast"): "nominal dof, like bnlearn; NaN when a table has an empty row or column",
             ("g_sq", "Rfast"): "nominal dof, like bnlearn",
             ("pearson_t", "ppcor"): "queries with an empty Z use stats::cor.test",
             ("g_sq", "pcalg (adaptDF)"): "pcalg adjusts dof by its own rule"}
    out += agreement_table("## Agreement, R packages", agreement(
        r["results"], ["pcalg", "bnlearn", "bnlearn (adf)", "pcalg (adaptDF)", "dHSIC", "Rfast", "ppcor", "comets"], r_exp,
        R_LABELS))
    out += ("\nThe agreement tables compare p-values on the same queries. A query with an error or NaN "
            "is not compared. The p-values come from the first run of each language. The R rows `bnlearn (adf)` and "
            "`pcalg (adaptDF)` use the adjusted degrees of freedom. They exist only for this comparison.\n")
    (d / "summary.md").write_text(out)
    summary = {"source": "benchmarks/summarize.py", "unit": "ms", "quick": bool(quick), "ecosystems": [eco_py, eco_r]}
    (d / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                                    encoding="utf-8")
    print(out)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
