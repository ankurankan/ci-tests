"""Time FastCIT against pgmpy, causal-learn and andrey-core on the shared queries.

Usage: python benchmarks/bench_python.py OUTDIR [--quick]

OUTDIR must hold the files written by benchmarks/data.py. The script writes OUTDIR/python.json.

Timing method: each engine runs 3 passes. Each pass builds new test objects (not timed, caches off
where an option exists). Each pass times every query once. The time of a query is the best of the 3
passes. The per-call result of a row is the median of those per-query times, in milliseconds. A query
that raises an error or returns NaN is counted and left out of the median.
The second result is the total per pass: setup (build the per-dataset state) plus all queries of the
group, once. The script reports the best of the 3 passes.
"""
import json
import os
import platform
import statistics
import subprocess
import sys
import time
import warnings
from importlib import metadata
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import fastcit as F  # noqa: E402
import pgmpy  # noqa: E402
import pgmpy.ci_tests as P  # noqa: E402
from andrey.core.ci import make_indep_test  # noqa: E402
from causallearn.utils.cit import CIT  # noqa: E402

PASSES = 3
CATEGORICAL = ("D0", "D1", "D2")


def version(dist):
    try:
        return metadata.version(dist)
    except metadata.PackageNotFoundError:
        return "unknown"


def sh(*cmd):
    try:
        return subprocess.run(list(cmd), capture_output=True, text=True).stdout.strip()
    except OSError:
        return ""


def cpus_allowed():
    """Return the CPU affinity: the Linux Cpus_allowed_list value and the scheduler affinity."""
    info = {}
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("Cpus_allowed_list"):
                info["cpus_allowed_list"] = line.split(":", 1)[1].strip()
    except OSError:
        pass
    if hasattr(os, "sched_getaffinity"):
        info["sched_getaffinity"] = sorted(os.sched_getaffinity(0))
    return info


def cpu_name():
    for line in Path("/proc/cpuinfo").read_text().splitlines() if Path("/proc/cpuinfo").exists() else []:
        if line.startswith("model name"):
            return line.split(":", 1)[1].strip()
    return platform.processor()


def load(outdir, name):
    return pd.read_csv(Path(outdir) / name)


# Every engine factory takes the data and returns run(query) -> (statistic, p_value).
# The factory runs outside the timer. run() runs inside the timer.


def fastcit_engine(ctor):
    def factory(data):
        ds = F.Dataset.from_pandas(data["df"])
        t = ctor(ds)

        def run(q):
            r = t.run_test(q["x"], q["y"], q["z"])
            return r.statistic, r.p_value
        return run
    return factory


def pgmpy_engine(ctor, **kw):
    def factory(data):
        t = ctor(data["pdf"], use_cache=False, **kw)

        def run(q):
            t.run_test(X=q["x"], Y=q["y"], Z=list(q["z"]))
            stat = getattr(t, "statistic_", None)
            return (None if stat is None else float(stat)), float(t.p_value_)
        return run
    return factory


def causallearn_engine(method):
    def factory(data):
        cols = {c: i for i, c in enumerate(data["df"].columns)}
        cit = CIT(data["df"].to_numpy(dtype=float), method)

        def run(q):
            return None, float(cit(cols[q["x"]], cols[q["y"]], [cols[c] for c in q["z"]]))
        return run
    return factory


def andrey_engine(name):
    def factory(data):
        cols = {c: i for i, c in enumerate(data["df"].columns)}
        tst = make_indep_test(name, data["df"].to_numpy(dtype=float))

        def run(q):
            return None, float(tst(cols[q["x"]], cols[q["y"]], [cols[c] for c in q["z"]]))
        return run
    return factory


# row -> (group, label, {engine: factory}, {engine: note})
ROWS = {
    "chi_square": ("discrete", "χ²", {
        "fastcit": fastcit_engine(lambda d: F.ChiSquared(d, yates=False)),
        "fastcit (yates)": fastcit_engine(lambda d: F.ChiSquared(d, yates=True)),
        "pgmpy": pgmpy_engine(P.ChiSquare),
        "causal-learn": causallearn_engine("chisq"),
        "andrey-core": andrey_engine("chisq"),
    }),
    "g_sq": ("discrete", "G²", {
        "fastcit": fastcit_engine(lambda d: F.LogLikelihood(d, yates=False)),
        "fastcit (yates)": fastcit_engine(lambda d: F.LogLikelihood(d, yates=True)),
        "pgmpy": pgmpy_engine(P.GSq),
        "causal-learn": causallearn_engine("gsq"),
        "andrey-core": andrey_engine("gsq"),
    }),
    "fisher_z": ("gaussian", "Fisher-z", {
        "fastcit": fastcit_engine(F.FisherZ),
        "pgmpy": pgmpy_engine(P.FisherZ),
        "causal-learn": causallearn_engine("fisherz"),
        "andrey-core": andrey_engine("fisherz"),
    }),
    "pearson_t": ("gaussian", "Pearson t", {
        "fastcit": fastcit_engine(F.PearsonCorrelation),
        "pgmpy": pgmpy_engine(P.Pearsonr),
        "andrey-core": andrey_engine("student_t"),
    }),
    "hsic": ("hsic", "HSIC (n = 300)", {
        "fastcit": fastcit_engine(F.HSIC),
        "pgmpy": pgmpy_engine(P.HSIC),
        "causal-learn": causallearn_engine("kci"),
        "andrey-core": andrey_engine("kci"),
    }),
    "kci_300": ("kci", "KCI (n = 300)", {
        "fastcit": fastcit_engine(F.KCI),
        "pgmpy": pgmpy_engine(P.KCI),
        "causal-learn": causallearn_engine("kci"),
        "andrey-core": andrey_engine("kci"),
    }),
    "kci_1000": ("kci_1000", "KCI (n = 1 000)", {
        "fastcit": fastcit_engine(F.KCI),
        "pgmpy": pgmpy_engine(P.KCI),
        "causal-learn": causallearn_engine("kci"),
        "andrey-core": andrey_engine("kci"),
    }),
    "gcm": ("gcm", "GCM", {
        "fastcit": fastcit_engine(F.GCM),
        "pgmpy": pgmpy_engine(P.GCM),
    }),
    "pillai": ("pillai", "Pillai", {
        "fastcit": fastcit_engine(F.PillaiTrace),
        "pgmpy": pgmpy_engine(P.PillaiTrace),
    }),
}
NOTES = {
    ("pillai", "pgmpy"): "random forest (pgmpy default); a different test from FastCIT (linear)",
}


def finite(x):
    return x is not None and np.isfinite(x)


def time_engine(factory, data, queries):
    """Run PASSES passes. Return the per-call median and the total time per pass.

    A query that raises an error or returns a NaN p-value in any pass is not part of the median.
    The total time per pass covers the setup (factory call) and all queries. It is the best pass.
    """
    n = len(queries)
    times = [[] for _ in range(n)]
    stats, ps = [None] * n, [None] * n
    err, nan = [False] * n, [False] * n
    totals, setups = [], []
    for pass_no in range(PASSES):
        t0 = time.perf_counter()
        run = factory(data)  # new objects each pass, so no state carries over
        setup = time.perf_counter() - t0
        total = setup
        for i, q in enumerate(queries):
            t0 = time.perf_counter()
            try:
                res = run(q)
            except Exception as exc:  # noqa: BLE001
                res = (None, None)
                if not err[i]:
                    print("  error:", type(exc).__name__, str(exc)[:100])
                err[i] = True
            dt = time.perf_counter() - t0
            total += dt
            times[i].append(dt)
            if not finite(res[1]) and not err[i]:
                nan[i] = True
            if pass_no == 0:
                stats[i] = res[0] if finite(res[0]) else None
                ps[i] = float(res[1]) if finite(res[1]) else None
        totals.append(total)
        setups.append(setup)
    ok = [i for i in range(n) if not err[i] and not nan[i]]
    best = [1e3 * min(t) for t in times]
    return {
        "median_ms": statistics.median(best[i] for i in ok) if ok else None,
        "total_ms": 1e3 * min(totals),
        "setup_ms": 1e3 * min(setups),
        "n_queries": n,
        "n_timed": len(ok),
        "errors": sum(err),
        "nan": sum(nan),
        "ms": best,
        "p": ps,
        "stat": stats,
    }


def pgmpy_commit():
    try:
        info = json.loads(metadata.distribution("pgmpy").read_text("direct_url.json") or "{}")
        commit = info.get("vcs_info", {}).get("commit_id")
        if commit:
            return commit[:8]
    except (metadata.PackageNotFoundError, ValueError):
        pass
    return os.environ.get("PGMPY_COMMIT", "unknown")


def fastcit_commit():
    """Return the commit of the checkout that holds this script, or the FASTCIT_COMMIT value.

    The commit of the checkout is not always the commit that built the installed wheel.
    Set FASTCIT_COMMIT when they differ.
    """
    env = os.environ.get("FASTCIT_COMMIT", "")
    if env:
        return env
    root = str(Path(__file__).resolve().parent)
    head = sh("git", "-C", root, "rev-parse", "--short", "HEAD") or "unknown"
    dirty = sh("git", "-C", root, "status", "--porcelain")
    return head + ("-dirty" if dirty else "")


def thread_info():
    info = {"env": {k: os.environ[k] for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")
                    if k in os.environ}, "fastcit": "single-threaded (no rayon)"}
    try:
        from threadpoolctl import threadpool_info
        info["pools"] = [f"{p.get('internal_api')} ({p.get('filepath', '').split('/')[-1]}), "
                         f"{p.get('num_threads')} threads" for p in threadpool_info()]
    except ImportError:
        info["pools"] = ["threadpoolctl not installed"]
    return info


def main(outdir, quick):
    outdir = Path(outdir)
    queries = json.loads((outdir / "queries.json").read_text())
    meta = {
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cpu": cpu_name(),
        "logical_cpus": os.cpu_count(),
        "os": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),
        "quick": quick,
        "passes": PASSES,
        "uptime_start": sh("uptime"),
        "versions": {
            "fastcit": version("fastcit"), "pgmpy": version("pgmpy") if version("pgmpy") != "unknown" else getattr(pgmpy, "__version__", "dev"),
            "causal-learn": version("causal-learn"), "andrey-core": version("andrey-core"),
            "numpy": np.__version__, "pandas": pd.__version__,
            "scipy": version("scipy"), "scikit-learn": version("scikit-learn"),
        },
        "commits": {
            "fastcit": fastcit_commit(),
            "pgmpy": pgmpy_commit(),
        },
        "threads": thread_info(),
        "affinity": cpus_allowed(),
    }
    results = {}
    cache = {}
    for row, (group, label, engines) in ROWS.items():
        qs = queries[group]["queries"][: 2 if quick else None]
        name = queries[group]["data"]
        if name not in cache:
            df = load(outdir, name)
            pdf = df.copy()
            if name == "discrete.csv":
                pdf = df.astype(str)  # pgmpy needs labels for discrete data
            for c in CATEGORICAL:
                if c in df.columns:
                    df[c] = df[c].astype("category")
                    pdf[c] = pdf[c].astype("category")
            cache[name] = {"df": df, "pdf": pdf}
        data = cache[name]
        results[row] = {"label": label, "engines": {}}
        for eng, factory in engines.items():
            res = time_engine(factory, data, qs)
            if (row, eng) in NOTES:
                res["note"] = NOTES[(row, eng)]
            if eng == "fastcit" and row in ("kci_300", "kci_1000"):
                # KCI is asymmetric in x and y. andrey-core picks its own orientation.
                t = F.KCI(F.Dataset.from_pandas(data["df"]))
                res["p_swapped"] = [t.run_test(q["y"], q["x"], q["z"]).p_value for q in qs]
            results[row]["engines"][eng] = res
            print(f"{row:10s} {eng:16s} median {res['median_ms']} ms, total {res['total_ms']:.2f} ms ({len(qs)} q, {res['errors']} errors, {res['nan']} NaN)", flush=True)
    meta["uptime_end"] = sh("uptime")
    (outdir / "python.json").write_text(json.dumps({"meta": meta, "results": results}, indent=1))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--quick"]
    if len(args) != 1:
        sys.exit(__doc__)
    main(args[0], "--quick" in sys.argv)
