"""Write summary.md from python.json and r.json.

Usage: python benchmarks/summarize.py DIR

DIR holds python.json and r.json. The script writes DIR/summary.md.
"""
import json
import math
import sys
from pathlib import Path

PY_ROWS = ["chi_square", "g_sq", "fisher_z", "pearson_t", "hsic", "kci_300", "kci_1000", "gcm", "pillai"]
PY_COLS = [("fastcit", "FastCIT"), ("pgmpy", "pgmpy dev"), ("causal-learn", "causal-learn"), ("andrey-core", "andrey-core")]
R_ROWS = ["chi_square", "g_sq", "fisher_z", "pearson_t", "hsic"]
R_COLS = [("fastcit", "FastCIT (R)"), ("pcalg", "pcalg"), ("bnlearn", "bnlearn"), ("dHSIC", "dHSIC")]
PY_LABELS = {"chi_square": "χ²", "g_sq": "G²", "fisher_z": "Fisher-z", "pearson_t": "Pearson t", "hsic": "HSIC (n = 300)",
             "kci_300": "KCI (n = 300)", "kci_1000": "KCI (n = 1 000)", "gcm": "GCM", "pillai": "Pillai"}
R_LABELS = {**PY_LABELS, "hsic": "HSIC (median width)"}

# Marks on cells and rows. The text of each mark is printed under the table.
PY_MARKS = {("pillai", "pgmpy"): "ᵃ", ("chi_square", "andrey-core"): "ᵇ", ("g_sq", "andrey-core"): "ᵇ",
            ("chi_square", "pgmpy"): "ᶜ", ("g_sq", "pgmpy"): "ᶜ",
            ("hsic", "causal-learn"): "ᵈ", ("hsic", "andrey-core"): "ᵈ"}
PY_ROW_MARKS = {"fisher_z": "ᵉ", "pearson_t": "ᵉ"}
R_MARKS = {("g_sq", "pcalg"): "ᶠ", ("chi_square", "bnlearn"): "ᶠ", ("g_sq", "bnlearn"): "ᶠ", ("hsic", "dHSIC"): "ᵈ"}
R_ROW_MARKS = {"fisher_z": "ᵉ", "pearson_t": "ᵉ"}
FOOT = {
    "ᵃ": "pgmpy runs a random-forest Pillai test. FastCIT runs a linear Pillai test. The two tests differ.",
    "ᵇ": "andrey-core χ² and G² use a different degrees-of-freedom rule from FastCIT.",
    "ᶜ": "pgmpy applies the Yates correction and cannot turn it off. FastCIT runs without it.",
    "ᵈ": "Different null approximation or kernel width rule from FastCIT.",
    "ᵉ": ("One-time setup is not part of the time. FastCIT, pcalg, causal-learn and andrey-core precompute "
          "the correlation matrix. pgmpy and bnlearn compute it in every call. See the total-per-pass table."),
    "ᶠ": "Uses the nominal degrees of freedom. FastCIT uses the adjusted degrees of freedom.",
}


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


def table(results, rows, cols, labels, marks, row_marks, key="median_ms"):
    out = "| Test | " + " | ".join(c[1] for c in cols) + " |\n|---|" + "---:|" * len(cols) + "\n"
    for r in rows:
        eng = results.get(r, {}).get("engines", {})
        cells = []
        for name, _ in cols:
            v = eng.get(name)
            cell = fmt(v[key]) if v else "—"
            if v and key == "median_ms":
                cell += marks.get((r, name), "")
            if v and (v["errors"] or v["nan"]):
                cell += "*"
            cells.append(cell)
        out += f"| {labels[r]}{row_marks.get(r, '') if key == 'median_ms' else ''} | " + " | ".join(cells) + " |\n"
    return out


def footnotes(marks, row_marks, extra=()):
    used = sorted(set(marks.values()) | set(row_marks.values()))
    lines = [f"{m} {FOOT[m]}" for m in used] + list(extra)
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
            if test in ("chi_square", "g_sq") and name == "pgmpy":
                base = eng["fastcit (yates)"]["p"]
                note = "compared with FastCIT with Yates on (pgmpy cannot turn it off)"
            elif test in ("kci_300", "kci_1000") and name == "andrey-core":
                # andrey-core picks the KCI orientation from the data; use the closer one
                d1 = maxdiff(base, eng[name]["p"])
                d2 = maxdiff(eng["fastcit"].get("p_swapped", base), eng[name]["p"])
                if d2 is not None and (d1 is None or d2 < d1):
                    base = eng["fastcit"]["p_swapped"]
                    note = "andrey-core uses the other x/y orientation; compared with FastCIT swapped"
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


def meta_block(title, m):
    lines = [f"- {title}: {m['date']}, {m['cpu']} ({m['logical_cpus']} logical CPUs), {m['os']}"]
    lines.append("  - versions: " + ", ".join(f"{k} {v}" for k, v in m["versions"].items()))
    lines.append("  - commits: " + ", ".join(f"{k} {v}" for k, v in m.get("commits", {}).items()))
    t = m.get("threads", {})
    lines.append(f"  - passes: {m['passes']}")
    lines.append(f"  - threads: FastCIT {t.get('fastcit', 'unknown')}; environment variables: {t.get('env') or 'none set'}")
    for k in ("pools", "blas", "lapack"):
        if t.get(k):
            v = t[k] if isinstance(t[k], list) else [t[k]]
            lines.append(f"  - {k}: " + "; ".join(str(x) for x in v))
    lines.append(f"  - uptime before: `{m['uptime_start'].strip()}`")
    lines.append(f"  - uptime after: `{m['uptime_end'].strip()}`")
    return "\n".join(lines)


def main(d):
    d = Path(d)
    py = json.loads((d / "python.json").read_text())
    r = json.loads((d / "r.json").read_text())
    out = "# FastCIT benchmark summary\n\n"
    out += ("The first two tables give the median time of one test call, in milliseconds. "
            "The last two tables give the total time of one pass, in milliseconds. Lower is better.\n\n")
    out += "## Setup\n\n" + meta_block("Python run", py["meta"]) + "\n" + meta_block("R run", r["meta"]) + "\n"
    quick = py["meta"].get("quick") or r["meta"].get("quick")
    out += "\nQuick run (2 queries per group): " + ("yes" if quick else "no") + "\n"
    out += "\n## Python packages, median time of one call\n\n" + table(py["results"], PY_ROWS, PY_COLS, PY_LABELS, PY_MARKS, PY_ROW_MARKS)
    failed = failed_list(py["results"])
    out += footnotes(PY_MARKS, PY_ROW_MARKS, ["\\* The engine raised an error or returned NaN on some queries. "
                                                "The median leaves them out. See the lists below."] if failed else [])
    out += "\n## R packages, median time of one call\n\n" + table(r["results"], R_ROWS, R_COLS, R_LABELS, R_MARKS, R_ROW_MARKS)
    failed_r = failed_list(r["results"])
    out += footnotes(R_MARKS, R_ROW_MARKS, ["\\* The engine raised an error or returned NaN on some queries. "
                                              "The median leaves them out. See the lists below."] if failed_r else [])
    out += ("\n## Python packages, total time of one pass\n\n"
            "Each pass builds the state of the engine (data conversion, test object, correlation matrix) "
            "and then runs all queries of the group once. The table shows the best of 3 passes.\n\n")
    out += table(py["results"], PY_ROWS, PY_COLS, PY_LABELS, {}, {}, key="total_ms")
    out += ("\n## R packages, total time of one pass\n\nThe table shows the best of 3 passes. "
            "bnlearn and dHSIC have no setup.\n\n")
    out += table(r["results"], R_ROWS, R_COLS, R_LABELS, {}, {}, key="total_ms")
    if failed or failed_r:
        out += "\n## Errors and NaN\n\n" + "\n".join(["Python:"] * bool(failed) + failed + ["R:"] * bool(failed_r) + failed_r) + "\n"
    else:
        out += "\n## Errors and NaN\n\nNo engine raised an error or returned NaN.\n"
    py_exp = {("chi_square", "andrey-core"): "different dof rule", ("g_sq", "andrey-core"): "different dof rule",
              ("pillai", "pgmpy"): "random forest, different test",
              ("hsic", "causal-learn"): "unconditional kci; kernel width or null approximation differs",
              ("hsic", "andrey-core"): "unconditional kci; kernel width or null approximation differs",
              ("kci_300", "causal-learn"): "kernel width or null approximation differs"}
    out += agreement_table("## Agreement, Python packages", agreement(
        py["results"], ["pgmpy", "causal-learn", "andrey-core"], py_exp, PY_LABELS))
    r_exp = {("chi_square", "bnlearn"): "default x2 uses nominal dof (see the adf row)",
             ("g_sq", "bnlearn"): "default mi uses nominal dof (see the adf row)",
             ("g_sq", "pcalg"): "nominal dof (adaptDF = FALSE)",
             ("hsic", "dHSIC"): "different kernel width or null approximation",
             ("g_sq", "pcalg (adaptDF)"): "pcalg adjusts dof by its own rule"}
    out += agreement_table("## Agreement, R packages", agreement(
        r["results"], ["pcalg", "bnlearn", "bnlearn (adf)", "pcalg (adaptDF)", "dHSIC"], r_exp, R_LABELS))
    out += ("\nThe agreement tables compare p-values on the same queries. A query with an error or NaN "
            "is not compared. The R rows `bnlearn (adf)` and `pcalg (adaptDF)` use the adjusted degrees "
            "of freedom. They exist only for this comparison.\n")
    (d / "summary.md").write_text(out)
    print(out)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
