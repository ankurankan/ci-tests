"""Time every test of bench_python.py at a grid of sample sizes n and of conditioning-set sizes |Z|.

Usage: python benchmarks/sweep_python.py OUTDIR [--quick] [--rows a,b,...] [--engines a,b,...] [--sweep n|z]
                                         [--seed N] [--out FILE]

OUTDIR must hold the files written by benchmarks/sweep_data.py. The script writes OUTDIR/FILE (default
sweep-python.json). It reuses the engines, the timing code and the metadata helpers of bench_python.py.
--quick runs the two smallest points of each sweep with 2 queries and 1 pass.
dowhy needs another interpreter: run `--engines dowhy,fastcit --rows gcm --out sweep-python-dowhy.json` there.

Sweeps (the grids are the "plan" of sweep-queries.json, written by sweep_data.py):
  n: n rows (the first n rows of the data file) at |Z| = 1 (HSIC: Z empty).
  z: |Z| = 0, 1, 2, 3, 4, 6, 8 at n = 1 000 (every row). HSIC has no |Z| sweep.
Every query of a point has exactly |Z| conditioning variables. 20 queries per point (kernel rows: 10).

Timing: 3 passes per point. The passes are the outer loop. Each pass runs the engines of the point in a new
random order (seeded). gc.collect() runs before each engine pass, outside the timer. Each engine pass builds new
test objects and times every query once. The time of a query is its best pass. The value of a point is the median
over the queries, in milliseconds. A query that raises an error or returns NaN is counted and left out.
Time budget: when the first pass of an engine at a point takes more than 60 s, the engine skips the remaining
passes of that point (the value comes from one pass) and all larger points of that sweep. Those points get
"median_ms": null and "skipped": "time budget".
Memory limit: a row with "n_max" in the plan (HSIC and KCI: 10 000) builds n x n matrices and does not run at a
larger n. Those points get "median_ms": null and "skipped": "memory limit". An engine that is already over the
time budget keeps "time budget".

Run file (JSON), shared with sweep_r.R:
{
 "meta": {date, cpu, logical_cpus, os, python, engines, quick, passes, seed, uptime_start/end, power,
          power_end, versions, helpers, commits, threads, affinity, fastcit_trees, harness_floor_ms,
          time_budget_s, kind: "sweep", ...},
 "results": {
  ROW: {"label": str,
        "sweeps": {
          "n" | "z": {"fixed": {"z": 1} | {"n": N},      # the fixed value of the other axis
                      "x": [n or |Z| of each point],
                      "engines": {ENGINE: [POINT, ...]}}}}   # one POINT per x, same order
 }
}
POINT = {"median_ms": float | null,    # median over the queries that gave a value (per call)
         "ms": [float | null, ...],     # best time of each query in ms; null for an error or NaN
         "errors": int, "nan": int,     # queries that raised an error, queries with a NaN p-value
         "n_queries": int, "n_timed": int, "passes": int,
         "setup_ms": float, "total_ms": float,   # best pass: the factory call (setup) and setup + all queries
         "skipped": null | "time budget" | "memory limit",
         "error": null | str,           # set when the engine could not run at all at this point
         "note": str}                   # only for engines with a known caveat (as in bench_python.py)
Engine keys are the ones of bench_python.py ("fastcit", "pgmpy", "causal-learn", ...).
"""
import argparse
import json
import os
import random
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

import bench_python as bp

PASSES = 3
BUDGET_S = 60.0

# row -> (label, {engine: factory}). The existing rows, with one KCI row, and the new Pearson-equivalence row.
ROWS = {}
for _row, (_group, _label, _engines) in bp.ROWS.items():
    if _row == "kci_300":
        ROWS["kci"] = ("KCI", _engines)
    elif _row not in ("kci_1000",):
        ROWS[_row] = (_label.replace(" (n = 300)", ""), _engines)
ROWS["pearson_equivalence"] = ("Pearson equivalence", {
    "fastcit": bp.fastcit_engine("PearsonEquivalence"),
    "pgmpy": bp.pgmpy_engine("PearsonrEquivalence"),
})


def point_result(**kw):
    out = {"median_ms": None, "ms": None, "errors": 0, "nan": 0, "n_queries": 0, "n_timed": 0, "passes": 0,
           "skipped": None, "error": None}
    out.update(kw)
    return out


def time_point(engines, data, queries, rng, passes, budget=None):
    """Run the passes over the engines at one point and return {engine: POINT}.

    The passes are the outer loop, with a new engine order in each pass. An engine whose first pass takes
    more than `budget` seconds skips the remaining passes and is marked "over" (the caller skips larger points).
    """
    budget = BUDGET_S if budget is None else budget
    states = {name: bp.new_state(len(queries)) for name in engines}
    failed, over = {}, set()
    active = list(engines)
    for pass_no in range(passes):
        order = list(active)
        rng.shuffle(order)
        for name in order:
            try:
                bp.time_pass(engines[name], data, queries, states[name], pass_no == 0)
            except Exception as exc:  # noqa: BLE001  the factory failed: the engine cannot run at this point
                failed[name] = f"{type(exc).__name__}: {str(exc)[:100]}"
                active.remove(name)
                continue
            if pass_no == 0 and states[name]["totals"][0] > budget:
                over.add(name)
                active.remove(name)
    out = {}
    for name, st in states.items():
        if name in failed:
            out[name] = point_result(error=failed[name], errors=len(queries), n_queries=len(queries))
            continue
        res = bp.result(st)
        ok = [not st["err"][i] and not st["nan"][i] for i in range(len(queries))]
        out[name] = point_result(median_ms=res["median_ms"], ms=[t if g else None for t, g in zip(res["ms"], ok)],
                                 errors=res["errors"], nan=res["nan"], n_queries=res["n_queries"],
                                 n_timed=res["n_timed"], passes=len(st["totals"]),
                                 setup_ms=res["setup_ms"], total_ms=res["total_ms"])
    return out, over


def skipped_point(n_queries, why="time budget"):
    return point_result(skipped=why, n_queries=n_queries)


def load_frames(outdir, spec):
    """Return {"df", "pdf"} of the full data file, as bench_python.py builds them."""
    df = pd.read_csv(Path(outdir) / spec["data"])
    pdf = df.astype(str) if spec["data"] == "sweep-discrete.csv" else df.copy()  # pgmpy needs labels
    for c in df.columns:
        if re.fullmatch(r"D\d", c):  # the categorical columns of the mixed data (not the column D of nonlinear)
            df[c] = df[c].astype("category")
            pdf[c] = pdf[c].astype("category")
    return {"df": df, "pdf": pdf}


def head(frames, n):
    """The first n rows of both frames (new objects, as the engines read them)."""
    out = {}
    for key, df in frames.items():
        part = df.iloc[:n].copy()
        for c in part.columns:
            if isinstance(part[c].dtype, pd.CategoricalDtype):
                part[c] = part[c].cat.remove_unused_categories()
        out[key] = part
    return out


def sweep_points(plan, z_grid, which, quick):
    """Return (fixed, x list, n of each point, k of each point) for one sweep of one row."""
    if which == "n":
        x = plan["n_grid"]
        fixed, ns, ks = {"z": plan["n_z"]}, x, [plan["n_z"]] * len(x)
    else:
        x = z_grid
        fixed, ns, ks = {"n": plan["z_n"]}, [plan["z_n"]] * len(x), x
    keep = 2 if quick else len(x)
    return fixed, x[:keep], ns[:keep], ks[:keep]


def build_meta(engines, quick, rows, seed, grids):
    dists = sorted({bp.ENGINE_DISTS.get(e, e) for e in engines})
    versions = {d: (bp.pgmpy_version() if d == "pgmpy" else bp.version(d)) for d in dists}
    versions.update({"numpy": np.__version__, "pandas": pd.__version__,
                     "scipy": bp.version("scipy"), "scikit-learn": bp.version("scikit-learn")})
    meta = {
        "kind": "sweep",
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cpu": bp.cpu_name(),
        "logical_cpus": os.cpu_count(),
        "os": f"{bp.platform.system()} {bp.platform.release()}",
        "python": bp.platform.python_version(),
        "engines": engines,
        "quick": quick,
        "passes": 1 if quick else PASSES,
        "time_budget_s": BUDGET_S,
        "seed": seed,
        "grids": grids,
        "uptime_start": bp.sh("uptime"),
        "power": bp.power_state(),
        "versions": versions,
        "helpers": {h: v for h in bp.HELPERS if (v := bp.version(h)) != "unknown"},
        "commits": {k: v for k, v in (("fastcit", bp.fastcit_commit() if "fastcit" in engines else None),
                                      ("pgmpy", bp.pgmpy_commit() if "pgmpy" in engines else None)) if v},
        "threads": bp.thread_info(),
        "affinity": bp.cpus_allowed(),
    }
    if rows:
        meta["rows"] = rows
    if "fastcit" in engines:
        meta["fastcit_trees"] = bp.fastcit_trees()
    return meta


def main(outdir, quick, engines, rows, sweeps, seed, out_name):
    outdir = Path(outdir)
    spec = json.loads((outdir / "sweep-queries.json").read_text())
    if "plan" not in spec:
        sys.exit("sweep-queries.json has no plan; run sweep_data.py again")
    if engines is None:
        engines = [e for e in bp.ENGINE_MODULES if bp.importable(e)]
        if "fastcit" not in engines:
            sys.exit("fastcit does not import in this interpreter, so the sweep would have no FastCIT line. "
                     "Install it, or name the engines with --engines.")
    missing = [e for e in engines if e not in bp.ENGINE_MODULES or not bp.importable(e)]
    if missing:
        sys.exit(f"engines not available in this interpreter: {missing}")
    unknown = [r for r in rows or [] if r not in ROWS]
    if unknown:
        sys.exit(f"unknown rows: {unknown}")
    passes, nq = (1, 2) if quick else (PASSES, None)
    meta = build_meta(engines, quick, rows, seed, spec["plan"]["grids"])
    floor_qs = spec["discrete"]["queries"]["1"][:nq]
    floor, _ = time_point({"noop": bp.noop_engine}, None, floor_qs, random.Random(f"{seed}:floor"), passes)
    meta["harness_floor_ms"] = floor["noop"]["median_ms"]
    print(f"harness floor: median {floor['noop']['median_ms']:.6f} ms", flush=True)
    results = {}
    cache = {}  # one data file at a time
    path = outdir / out_name

    def save(done=False):
        if done:
            meta["uptime_end"] = bp.sh("uptime")
            meta["power_end"] = bp.power_state()
        path.write_text(json.dumps({"meta": meta, "results": results}, indent=1))

    for row, (label, row_engines) in ROWS.items():
        todo = {e: f for e, f in row_engines.items() if e in engines}
        if not todo or (rows and row not in rows):
            continue
        plan = spec["plan"]["rows"][row]
        gspec = spec[plan["gen"]]
        if cache.get("name") != gspec["data"]:
            cache.clear()
            cache.update(name=gspec["data"], frames=load_frames(outdir, gspec))
        results[row] = {"label": label, "sweeps": {}}
        for which in sweeps:
            if which == "z" and not plan["z_n"]:
                continue
            fixed, xs, ns, ks = sweep_points(plan, spec["plan"]["grids"]["z"], which, quick)
            # A data file capped by --max-n has fewer rows: drop the points it cannot serve.
            keep = [i for i, n in enumerate(ns) if n <= gspec["rows"]]
            xs, ns, ks = [xs[i] for i in keep], [ns[i] for i in keep], [ks[i] for i in keep]
            series = {e: [] for e in todo}
            dead = set()  # engines over the time budget
            for x, n, k in zip(xs, ns, ks):
                qs = gspec["queries"][str(k)][:nq]
                assert all(len(q["z"]) == k for q in qs), f"{row} {which} x={x}: a query does not have {k} conditioning variables"
                too_big = bool(plan.get("n_max")) and n > plan["n_max"]  # the row needs too much memory at this n
                live = {} if too_big else {e: f for e, f in todo.items() if e not in dead}
                res, over = time_point(live, head(cache["frames"], n), qs,
                                       random.Random(f"{seed}:{row}:{which}:{x}"), passes) if live else ({}, set())
                dead |= over
                for e in todo:
                    p = res.get(e) or skipped_point(len(qs), "memory limit" if too_big and e not in dead
                                                    else "time budget")
                    if (row, e) in bp.NOTES:
                        p["note"] = bp.NOTES[(row, e)]
                    series[e].append(p)
                    msg = f"skipped ({p['skipped']})" if p["skipped"] else f"median {p['median_ms']} ms"
                    print(f"{row:19s} {which} x={x:<7} {e:16s} {msg} ({p['n_queries']} q, {p['errors']} errors, "
                          f"{p['nan']} NaN)" + (f" [{p['error']}]" if p["error"] else ""), flush=True)
            results[row]["sweeps"][which] = {"fixed": fixed, "x": xs, "engines": series}
            save()
    save(done=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("outdir")
    ap.add_argument("--quick", action="store_true", help="two smallest points per sweep, 2 queries, 1 pass")
    ap.add_argument("--engines", help="comma-separated engine names (default: all importable)")
    ap.add_argument("--rows", help="comma-separated row names (default: all rows)")
    ap.add_argument("--sweep", choices=["n", "z"], help="run one sweep only (default: both)")
    ap.add_argument("--seed", type=int, default=1, help="seed of the engine order in each pass (default 1)")
    ap.add_argument("--out", default="sweep-python.json", help="file name inside OUTDIR")
    a = ap.parse_args()
    main(a.outdir, a.quick, a.engines.split(",") if a.engines else None, a.rows.split(",") if a.rows else None,
         [a.sweep] if a.sweep else ["n", "z"], a.seed, a.out)
