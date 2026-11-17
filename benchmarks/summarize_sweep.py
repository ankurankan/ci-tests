"""Write sweep.json and sweep.md from the run files of the sweep benchmark.

Usage: python benchmarks/summarize_sweep.py DIR

DIR holds the run files of sweep_python.py and sweep_r.R (the shape is in the docstring of sweep_python.py):
  sweep-python.json         main Python interpreter
  sweep-python-dowhy.json   optional, from Python 3.11 (dowhy does not support 3.14): dowhy and a FastCIT reference
  sweep-r.json              R
A language without a run file is left out. The script writes DIR/sweep.json (the data of the chart on the
documentation page "Benchmark") and DIR/sweep.md (the same numbers as tables). Both come from the same data.

The dowhy run adds the series "dowhy" to the Python row gcm. Its FastCIT run is a same-interpreter reference.
It is not a series. It goes to meta.python.other_runs[].reference, as summarize.py does for the main benchmark.
The engine "fastcit (yates)" of the run files is not shown. The series "fastcit" is FastCIT without the Yates
correction, as in the run files.

sweep.json (unit: ms; "meta", "languages" and the keys below are stable, the chart and the tests read them):
{
 "source": "benchmarks/summarize_sweep.py", "unit": "ms", "quick": bool,
 "meta": {"python" | "r": {
     "date", "cpu", "logical_cpus", "os",
     "interpreter": "Python 3.14.2" | "R version 4.5.3 ...",
     "versions": {package: version}, "commits", "passes", "budget_s", "quick", "seed", "power", "power_end",
     "threads", "affinity", "helpers", "fastcit_trees", "harness_floor_ms",        # when the run file has them
     "other_runs": [ {group, date, interpreter, versions, ..., "reference":       # Python only (dowhy run)
                      {ROW: {SWEEP: {"x": [..], "values": [ms | null, ..]}}}} ]}},
 "languages": [ {"key": "python" | "r", "label": "Python" | "R", "rows": [
   {"key": ROW, "label": str,
    "sweeps": {"n" | "z": {                       # "z" is missing for hsic, "n" has fixed {"z": 1} (hsic {"z": 0})
        "fixed": {"z": 1} | {"n": N},             # the value of the other axis
        "x": [n or |Z| of each point],
        "series": [ {"engine": key, "label": str,
                     "values": [ms | null, ...],  # median over the queries, aligned to x; null: no result
                     "skipped": [str | null, ...],  # aligned to x; the reason when the value is null:
                                                    #   "time budget" | "error: TEXT" | "all queries NaN"
                                                    #   | "all queries raised errors"
                     "notes": [str, ...],         # engine-level caveats, same for every point
                     # Added fields:
                     "passes": [int, ...],        # passes behind each value. 1 after the time budget (the value
                                                  # is kept); the chart marks values whose passes < meta passes
                     "excluded": [int, ...]}]}}}  # queries left out of the median (errors + NaN) at each point
 ]} ]
}
Series order: "fastcit" first, then the engines in the column order of the tables of summarize.py (Python:
pgmpy, causal-learn, gcastle, tigramite, pingouin, hyppo, dowhy; R: pcalg, bnlearn, dHSIC, Rfast, ppcor, comets).
An engine that is in no list goes last, in name order. Row order: the row order of summarize.py, with the new rows
(pearson_equivalence after pearson_t, kci for both KCI rows). Labels: "FastCIT" in both languages.
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import summarize as sm  # noqa: E402  (no side effects on import; fmt and the notes are reused)

LANGS = [("python", "Python", "sweep-python.json", sm.PY_COLS), ("r", "R", "sweep-r.json", sm.R_COLS)]
DOWHY_FILE = "sweep-python-dowhy.json"
ROWS = ["chi_square", "g_sq", "cressie_read", "freeman_tukey", "modified_ll", "fisher_z", "pearson_t",
        "pearson_equivalence", "hsic", "kci", "gcm", "pillai"]
LABELS = {**sm.PY_LABELS, "hsic": "HSIC", "kci": "KCI", "pearson_equivalence": "Pearson equivalence"}
LABELS_R = {**LABELS, "chi_square": "χ²", "g_sq": "G²"}
HIDDEN = ("fastcit (yates)",)  # engines of the run files that the sweep does not show
AXES = ("n", "z")
MARKS = ["ᵃ", "ᵇ", "ᶜ", "ᵈ", "ᵉ", "ᶠ", "ᵍ", "ʰ", "ⁱ", "ʲ"]  # marks of the engine notes, per table
ONE_PASS, BUDGET, FAILED, EXCLUDED = "†", "‡", "§", "*"
META_KEYS = ("date", "cpu", "logical_cpus", "os", "versions", "commits", "quick", "seed", "power", "power_end",
             "threads", "affinity", "helpers", "fastcit_trees", "harness_floor_ms")
# Notes of the existing summary that apply to the engine of a row (summarize.py marks). Pillai has its own note
# in the run file, so the mark "ᵃ" is not repeated.
MARK_NOTES = {
    "python": {("kci" if r == "kci_300" else r, e): m.replace("ᵃ", "") for (r, e), m in sm.PY_MARKS.items()
               if r != "kci_1000"},
    "r": dict(sm.R_MARKS),
}


def good(x):
    return x is not None and not (isinstance(x, float) and math.isnan(x))


def load(d, name):
    path = Path(d) / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def reason(p):
    """Return why a point has no value (None if it has one)."""
    if good(p.get("median_ms")):
        return None
    if p.get("skipped"):
        return str(p["skipped"])
    if p.get("error"):
        return f"error: {p['error']}"
    if p.get("nan") and not p.get("errors"):
        return "all queries NaN"
    if p.get("errors") and not p.get("nan"):
        return "all queries raised errors"
    if p.get("errors") or p.get("nan"):
        return "all queries NaN" if p["nan"] >= p["errors"] else "all queries raised errors"
    return "no result"


def notes_for(lang, row, name, points):
    notes = []
    for p in points:
        if p.get("note") and p["note"] not in notes:
            notes.append(p["note"])
    marks = MARK_NOTES[lang].get((row, name), "")
    if row in sm.YATES_ROWS and name in sm.YATES_ENGINES and lang == "python":
        marks += "ᵇ"
    for m in dict.fromkeys(marks):
        if m in sm.FOOT and sm.FOOT[m] not in notes:
            notes.append(sm.FOOT[m])
    return notes


def engine_order(cols, names):
    order = [k for k, _ in cols if k in names]
    return order + sorted(n for n in names if n not in order)


def make_series(lang, cols, row, sweep, names):
    labels = dict(cols)
    out = []
    for name in engine_order(cols, [n for n in names if n not in HIDDEN]):
        pts = sweep["engines"][name]
        out.append({
            "engine": name,
            "label": "FastCIT" if name == "fastcit" else labels.get(name, name),
            "values": [p["median_ms"] if good(p.get("median_ms")) else None for p in pts],
            "skipped": [reason(p) for p in pts],
            "notes": notes_for(lang, row, name, pts),
            "passes": [p.get("passes", 0) for p in pts],
            "excluded": [(p.get("errors") or 0) + (p.get("nan") or 0) for p in pts],
        })
    out.sort(key=lambda s: s["engine"] != "fastcit")  # stable: FastCIT first
    return out


def run_meta(data, interpreter):
    m = data["meta"]
    out = {k: m[k] for k in META_KEYS if k in m}
    out.update({"interpreter": interpreter, "passes": m.get("passes"), "budget_s": m.get("time_budget_s")})
    return out


def merge_dowhy(lang_meta, results, extra):
    """Add the dowhy series to the Python rows. Keep its FastCIT run as a reference in meta."""
    m = run_meta(extra, "Python " + str(extra["meta"].get("python", "unknown")))
    m.update({"group": "python-dowhy", "engines": extra["meta"].get("engines")})
    reference = {}
    for row, res in extra["results"].items():
        if row not in results:
            sys.exit(f"{DOWHY_FILE}: row {row} is not in sweep-python.json")
        for axis, sweep in res["sweeps"].items():
            target = results[row]["sweeps"].get(axis)
            if target is None or target["x"] != sweep["x"]:
                sys.exit(f"{DOWHY_FILE}: the {axis} grid of {row} differs from sweep-python.json")
            for name, pts in sweep["engines"].items():
                if name in target["engines"]:  # FastCIT: a reference in the same interpreter
                    reference.setdefault(row, {})[axis] = {
                        "x": sweep["x"], "values": [p["median_ms"] if good(p.get("median_ms")) else None
                                                    for p in pts]}
                else:
                    target["engines"][name] = pts
    m["reference"] = reference
    lang_meta.setdefault("other_runs", []).append(m)


def build(d):
    languages, meta = [], {}
    quick = False
    for key, label, fname, cols in LANGS:
        data = load(d, fname)
        if data is None:
            continue
        m = data["meta"]
        interpreter = "Python " + str(m.get("python", "unknown")) if key == "python" else str(m.get("r", "R"))
        meta[key] = run_meta(data, interpreter)
        results = data["results"]
        extra = load(d, DOWHY_FILE) if key == "python" else None
        if extra:
            merge_dowhy(meta[key], results, extra)
        quick = quick or any(bool(x.get("quick")) for x in [m] + ([extra["meta"]] if extra else []))
        names = LABELS if key == "python" else LABELS_R
        rows = []
        for row in sorted(results, key=lambda r: ROWS.index(r) if r in ROWS else len(ROWS)):
            sweeps = {}
            for axis in AXES:
                sw = results[row]["sweeps"].get(axis)
                if sw is None:
                    continue
                sweeps[axis] = {"fixed": sw["fixed"], "x": sw["x"],
                                "series": make_series(key, cols, row, sw, list(sw["engines"]))}
            rows.append({"key": row, "label": names.get(row, results[row]["label"]), "sweeps": sweeps})
        languages.append({"key": key, "label": label, "rows": rows})
    if not languages:
        sys.exit(f"{d}: no run file (sweep-python.json or sweep-r.json)")
    return {"source": "benchmarks/summarize_sweep.py", "unit": "ms", "quick": quick, "meta": meta,
            "languages": languages}


def num(x):
    return sm.fmt(float(x)) if isinstance(x, float) else f"{x:,}".replace(",", " ")


def title(lang, row, axis, sweep):
    fixed = sweep["fixed"]
    if axis == "n":
        other = "Z empty" if fixed.get("z") == 0 else f"|Z| = {fixed['z']}"
        return f"{lang['label']}, {row['label']}, sample size ({other})"
    return f"{lang['label']}, {row['label']}, conditioning-set size (n = {num(fixed['n'])})"


def table(sweep, meta):
    """Return the Markdown table of one sweep and the footnotes of its marks."""
    used, notes = set(), []
    xs = sweep["x"]
    head = "| Package | " + " | ".join(num(x) for x in xs) + " |\n|---|" + "---:|" * len(xs) + "\n"
    out = head
    for s in sweep["series"]:
        marks = ""
        for text in s["notes"]:
            if text not in [t for _, t in notes]:
                notes.append((MARKS[len(notes)], text))
            marks += next(m for m, t in notes if t == text)
        cells = []
        for v, why, passes, excl in zip(s["values"], s["skipped"], s["passes"], s["excluded"]):
            if v is None:
                mark = BUDGET if why == "time budget" else FAILED
                used.add(mark)
                cells.append("—" + mark)
                continue
            cell = sm.fmt(v)
            if meta.get("passes") and passes < meta["passes"]:
                cell += ONE_PASS
                used.add(ONE_PASS)
            if excl:
                cell += EXCLUDED
                used.add(EXCLUDED)
            cells.append(cell)
        out += f"| {s['label']}{marks} | " + " | ".join(cells) + " |\n"
    lines = [f"- {m} {t}" for m, t in notes]
    texts = {ONE_PASS: f"The first pass took more than {num(int(meta.get('budget_s') or 60))} s. "
                       "The cell comes from one pass. Larger points are missing.",
             BUDGET: "No result. The engine skipped this point after it passed the time budget.",
             FAILED: "No result. Every query raised an error or returned NaN.",
             EXCLUDED: "Some queries raised an error or returned NaN. The median uses the other queries."}
    shown = {EXCLUDED: "\\*"}
    lines += [f"- {shown.get(m, m)} {texts[m]}" for m in (ONE_PASS, BUDGET, FAILED, EXCLUDED) if m in used]
    return out + ("\n" + "\n".join(lines) + "\n" if lines else "")


def markdown(data):
    out = "# FastCIT sweep benchmark\n\n"
    out += ("The tables give the median time of one test call, in milliseconds. Lower is better. "
            "Each test has one table for the sample size n and one for the conditioning-set size |Z|. "
            "Each column is one value of n or |Z|.\n\n")
    out += ("Each cell is the median over the queries of a point. Each query keeps its fastest pass. "
            "An engine that passes the time budget skips the larger points. "
            "— means no result. Other marks are explained under each table.\n\n")
    if data["quick"]:
        out += "This is a quick run with few queries and one pass. Do not use its numbers.\n\n"
    out += "## Setup\n\n"
    for lang in data["languages"]:
        m = data["meta"][lang["key"]]
        out += (f"- {lang['label']}: {m['interpreter']}, {m.get('cpu', 'unknown CPU')} "
                f"({m.get('logical_cpus', '?')} logical CPUs), {m.get('os', 'unknown OS')}, {m.get('date', 'no date')}; "
                f"passes per point: {m.get('passes')}; time budget: {num(int(m.get('budget_s') or 0))} s.\n")
        out += "  - versions: " + ", ".join(f"{k} {v}" for k, v in m.get("versions", {}).items()) + "\n"
        for o in m.get("other_runs", []):
            out += (f"  - dowhy run: {o['interpreter']}, {o.get('date', 'no date')}, versions: "
                    + ", ".join(f"{k} {v}" for k, v in o.get("versions", {}).items()) + "\n")
            for row, axes in o["reference"].items():
                for axis, ref in axes.items():
                    out += (f"  - same-interpreter FastCIT reference ({row}, {axis}, not a table row): "
                            + ", ".join(sm.fmt(v) if v is not None else "—" for v in ref["values"]) + " ms\n")
    for lang in data["languages"]:
        meta = data["meta"][lang["key"]]
        for row in lang["rows"]:
            for axis, sweep in row["sweeps"].items():
                out += f"\n### {title(lang, row, axis, sweep)}\n\n" + table(sweep, meta)
    return out


def main(d):
    d = Path(d)
    data = build(d)
    (d / "sweep.json").write_text(json.dumps(data, ensure_ascii=False, indent=1, allow_nan=False) + "\n",
                                  encoding="utf-8")
    (d / "sweep.md").write_text(markdown(data), encoding="utf-8")
    return data


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
