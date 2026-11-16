"""Time FastCIT against pgmpy, causal-learn, gcastle, tigramite, pingouin, hyppo and dowhy on the shared queries.

Usage: python benchmarks/bench_python.py OUTDIR [--quick] [--engines a,b,...] [--rows a,b,...] [--seed N] [--out FILE]

OUTDIR must hold the files written by benchmarks/data.py. The script writes OUTDIR/FILE (default python.json).
--engines picks the engines to run. The default is every engine whose package imports in this interpreter.
--rows picks the tests (rows) to run. The default is every row.
dowhy does not support Python 3.14. Run it in a second interpreter with
`--engines dowhy,fastcit --rows gcm --out python-dowhy-1.json`. FastCIT runs there as a reference in the same
interpreter. benchmarks/summarize.py merges the files. Run the script three times, each in a new process, with
--seed 1, 2 and 3 and --out NAME-1.json, NAME-2.json and NAME-3.json.

Timing method: each row runs 5 passes. Each pass runs the engines of the row in a new random order (from --seed),
so that a slow period of the machine spreads over the engines. Before each engine pass, the script runs
gc.collect() outside the timer. Each engine pass builds new test objects (timed as setup, caches off where an
option exists) and then times every query once. The time of a query is the best of the 5 passes. The per-call
result of a row is the median of those per-query times, in milliseconds. A query that raises an error or returns
NaN is counted and left out of the median.
The second result is the total per pass: setup (build the per-dataset state) plus all queries of the
group, once. The script reports the best of the 5 passes.
The script also times a no-op engine through the same code (the harness floor) and records its median.
It does not subtract the floor from any result.
"""
import argparse
import gc
import importlib
import json
import os
import platform
import random
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

PASSES = 5
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


def read_text(path):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return "unknown"


def power_state():
    """Return the power state: AC adapter, power profile, and the governor and EPP of CPU 0 (Linux)."""
    supplies = [p for p in Path("/sys/class/power_supply").glob("*") if read_text(p / "type") == "Mains"]
    cpu0 = Path("/sys/devices/system/cpu/cpu0/cpufreq")
    return {
        "ac_online": read_text(supplies[0] / "online") if supplies else "unknown",
        "profile": sh("powerprofilesctl", "get") or "unknown",
        "governor": read_text(cpu0 / "scaling_governor"),
        "epp": read_text(cpu0 / "energy_performance_preference"),
    }


def cpu_name():
    for line in Path("/proc/cpuinfo").read_text().splitlines() if Path("/proc/cpuinfo").exists() else []:
        if line.startswith("model name"):
            return line.split(":", 1)[1].strip()
    return platform.processor()


def load(outdir, name):
    return pd.read_csv(Path(outdir) / name)


# Every engine factory takes the data and returns run(query) -> (statistic, p_value).
# The factory runs outside the timer. run() runs inside the timer.
# Packages import inside the factories, so a missing package only removes its own engines.

# engine -> module that must import for the engine to run
ENGINE_MODULES = {
    "fastcit": "fastcit",
    "fastcit (yates)": "fastcit",
    "pgmpy": "pgmpy.ci_tests",
    "causal-learn": "causallearn.utils.cit",
    "gcastle": "castle.common.independence_tests",
    "tigramite": "tigramite.independence_tests.parcorr",
    "pingouin": "pingouin",
    "hyppo": "hyppo.independence",
    "dowhy": "dowhy.gcm.independence_test",
}
# engine -> name of the distribution whose version the run records
ENGINE_DISTS = {"fastcit (yates)": "fastcit"}


def importable(engine):
    try:
        importlib.import_module(ENGINE_MODULES[engine])
        return True
    except Exception:  # noqa: BLE001  any import failure means the engine cannot run here
        return False


def fastcit_engine(name, **kw):
    def factory(data):
        import fastcit as F
        ds = F.Dataset.from_pandas(data["df"])
        t = getattr(F, name)(ds, **kw)

        def run(q):
            r = t.run_test(q["x"], q["y"], q["z"])
            return r.statistic, r.p_value
        return run
    return factory


def pgmpy_engine(name, **kw):
    def factory(data):
        import pgmpy.ci_tests as P
        t = getattr(P, name)(data["pdf"], use_cache=False, **kw)

        def run(q):
            t.run_test(X=q["x"], Y=q["y"], Z=list(q["z"]))
            stat = getattr(t, "statistic_", None)
            return (None if stat is None else float(stat)), float(t.p_value_)
        return run
    return factory


def causallearn_engine(method):
    def factory(data):
        from causallearn.utils.cit import CIT
        cols = {c: i for i, c in enumerate(data["df"].columns)}
        cit = CIT(data["df"].to_numpy(dtype=float), method)

        def run(q):
            return None, float(cit(cols[q["x"]], cols[q["y"]], [cols[c] for c in q["z"]]))
        return run
    return factory


def gcastle_engine(name):
    def factory(data):
        from castle.common.independence_tests import CITest
        cols = {c: i for i, c in enumerate(data["df"].columns)}
        arr = data["df"].to_numpy(dtype=float)
        fn = getattr(CITest, name)

        def run(q):
            stat, _, p = fn(arr, cols[q["x"]], cols[q["y"]], [cols[c] for c in q["z"]])
            return stat, float(p)
        return run
    return factory


def tigramite_engine(kind):
    def factory(data):
        import tigramite.data_processing as pp
        cols = {c: i for i, c in enumerate(data["df"].columns)}
        arr = data["df"].to_numpy(dtype=float)
        if kind == "parcorr":
            from tigramite.independence_tests.parcorr import ParCorr
            test, frame = ParCorr(significance="analytic"), pp.DataFrame(arr)
        else:
            from tigramite.independence_tests.gsquared import Gsquared
            test = Gsquared(significance="analytic")
            frame = pp.DataFrame(arr, data_type=np.ones(arr.shape, dtype=int))
        test.set_dataframe(frame)  # building the data frame is setup

        def run(q):
            stat, p = test.run_test(X=[(cols[q["x"]], 0)], Y=[(cols[q["y"]], 0)],
                                    Z=[(cols[c], 0) for c in q["z"]], tau_max=0)
            return float(stat), float(p)
        return run
    return factory


def pingouin_engine(data):
    import pingouin as pg
    df = data["df"]

    def run(q):
        r = pg.partial_corr(data=df, x=q["x"], y=q["y"], covar=list(q["z"]) or None)
        return float(r["r"].iloc[0]), float(r["p_val"].iloc[0])
    return run


def hyppo_engine(data):
    from hyppo.independence import Hsic
    cols = {c: data["df"][[c]].to_numpy(dtype=float) for c in data["df"].columns}  # setup
    test = Hsic()

    def run(q):
        stat, p = test.test(cols[q["x"]], cols[q["y"]])
        return float(stat), float(p)
    return run


def dowhy_engine(data):
    from dowhy.gcm.independence_test import generalised_cov_based
    from dowhy.gcm.ml import create_linear_regressor
    cols = {c: data["df"][[c]].to_numpy(dtype=float) for c in data["df"].columns}  # setup

    def run(q):
        z = np.hstack([cols[c] for c in q["z"]]) if q["z"] else None
        p = generalised_cov_based(cols[q["x"]], cols[q["y"]], z, prediction_model_X=create_linear_regressor,
                                  prediction_model_Y=create_linear_regressor)
        return None, float(p)
    return run


def discrete_row(label, fc_name, pg_name, pg_kw, gc_name, cl_name=None, extra=None):
    engines = {
        "fastcit": fastcit_engine(fc_name, yates=False),
        "fastcit (yates)": fastcit_engine(fc_name, yates=True),
        "pgmpy": pgmpy_engine(pg_name, **pg_kw),
    }
    if cl_name:
        engines["causal-learn"] = causallearn_engine(cl_name)
    engines["gcastle"] = gcastle_engine(gc_name)
    engines.update(extra or {})
    return ("discrete", label, engines)


# row -> (group, label, {engine: factory})
ROWS = {
    "chi_square": discrete_row("χ²", "ChiSquared", "ChiSquare", {}, "chi2_test", "chisq"),
    "g_sq": discrete_row("G²", "LogLikelihood", "GSq", {}, "g2_test", "gsq",
                         {"tigramite": tigramite_engine("gsquared")}),
    "cressie_read": discrete_row("Cressie-Read", "CressieRead", "PowerDivergence", {"lambda_": "cressie-read"},
                                 "cressie_read"),
    # pgmpy dev a67c17d9 misspells the alias ("freeman-tuckey"), so the script passes lambda_=-0.5 instead.
    "freeman_tukey": discrete_row("Freeman-Tukey", "FreemanTukey", "PowerDivergence", {"lambda_": -0.5},
                                  "freeman_tukey"),
    "modified_ll": discrete_row("Modified log-likelihood", "ModifiedLikelihood", "ModifiedLogLikelihood", {},
                                "modify_log_likelihood"),
    "fisher_z": ("gaussian", "Fisher-z", {
        "fastcit": fastcit_engine("FisherZ"),
        "pgmpy": pgmpy_engine("FisherZ"),
        "causal-learn": causallearn_engine("fisherz"),
        "gcastle": gcastle_engine("fisherz_test"),
    }),
    "pearson_t": ("gaussian", "Pearson t", {
        "fastcit": fastcit_engine("PearsonCorrelation"),
        "pgmpy": pgmpy_engine("Pearsonr"),
        "tigramite": tigramite_engine("parcorr"),
        "pingouin": pingouin_engine,
    }),
    "hsic": ("hsic", "HSIC (n = 300)", {
        "fastcit": fastcit_engine("HSIC", bandwidth="median"),
        "pgmpy": pgmpy_engine("HSIC", bandwidth="median"),
        "causal-learn": causallearn_engine("kci"),
        "hyppo": hyppo_engine,
    }),
    "kci_300": ("kci", "KCI (n = 300)", {
        "fastcit": fastcit_engine("KCI"),
        "pgmpy": pgmpy_engine("KCI"),
        "causal-learn": causallearn_engine("kci"),
    }),
    "kci_1000": ("kci_1000", "KCI (n = 1 000)", {
        "fastcit": fastcit_engine("KCI"),
        "pgmpy": pgmpy_engine("KCI"),
        "causal-learn": causallearn_engine("kci"),
    }),
    "gcm": ("gcm", "GCM", {
        "fastcit": fastcit_engine("GCM"),
        "pgmpy": pgmpy_engine("GCM"),
        "dowhy": dowhy_engine,
    }),
    "pillai": ("pillai", "Pillai", {
        "fastcit": fastcit_engine("PillaiTrace"),
        "pgmpy": pgmpy_engine("PillaiTrace"),
    }),
}
NOTES = {
    ("pillai", "pgmpy"): "random forest (pgmpy default); a different test from FastCIT (linear)",
}


def finite(x):
    return x is not None and np.isfinite(x)


def noop_engine(data):
    """An engine that does nothing. Its time is the cost of the timing code itself (the harness floor)."""
    def run(q):
        return 0.0, 1.0
    return run


def new_state(n):
    return {"times": [[] for _ in range(n)], "stats": [None] * n, "ps": [None] * n,
            "err": [False] * n, "nan": [False] * n, "totals": [], "setups": []}


def time_pass(factory, data, queries, st, first):
    """Time one pass of one engine: build its state (setup), then run every query once."""
    gc.collect()  # outside the timer
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
            if not st["err"][i]:
                print("  error:", type(exc).__name__, str(exc)[:100])
            st["err"][i] = True
        dt = time.perf_counter() - t0
        total += dt
        st["times"][i].append(dt)
        if not finite(res[1]) and not st["err"][i]:
            st["nan"][i] = True
        if first:
            st["stats"][i] = res[0] if finite(res[0]) else None
            st["ps"][i] = float(res[1]) if finite(res[1]) else None
    st["totals"].append(total)
    st["setups"].append(setup)


def result(st):
    """Return the per-call median and the total time per pass of one engine.

    A query that raises an error or returns a NaN p-value in any pass is not part of the median.
    The total time per pass covers the setup (factory call) and all queries. It is the best pass.
    """
    n = len(st["times"])
    ok = [i for i in range(n) if not st["err"][i] and not st["nan"][i]]
    best = [1e3 * min(t) for t in st["times"]]
    return {
        "median_ms": statistics.median(best[i] for i in ok) if ok else None,
        "total_ms": 1e3 * min(st["totals"]),
        "setup_ms": 1e3 * min(st["setups"]),
        "n_queries": n,
        "n_timed": len(ok),
        "errors": sum(st["err"]),
        "nan": sum(st["nan"]),
        "ms": best,
        "p": st["ps"],
        "stat": st["stats"],
    }


def time_row(engines, data, queries, rng):
    """Run PASSES passes over the engines of one row and return {engine: result}.

    The passes are the outer loop. Each pass runs the engines in a new random order, so that a slow period of
    the machine does not hit one engine only.
    """
    states = {name: new_state(len(queries)) for name in engines}
    for pass_no in range(PASSES):
        order = list(engines)
        rng.shuffle(order)
        for name in order:
            time_pass(engines[name], data, queries, states[name], pass_no == 0)
    return {name: result(st) for name, st in states.items()}


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


TREE_PATHS = ("crates/ci-core", "crates/ci-python")


def fastcit_trees():
    """Return the git tree hash of each crate that the wheel builds from.

    A tree hash depends only on the content of the folder. It stays valid after a squash merge,
    when the commit hash of the branch no longer exists. Check it with `git rev-parse <commit>:<path>`.
    FASTCIT_COMMIT, when set, names the commit that the hashes come from.
    """
    root = str(Path(__file__).resolve().parent)
    rev = os.environ.get("FASTCIT_COMMIT", "").removesuffix("-dirty") or "HEAD"
    return {path: sh("git", "-C", root, "rev-parse", f"{rev}:{path}") or "unknown" for path in TREE_PATHS}


# Helper packages that the optional engines need. The run records the versions that are installed.
HELPERS = ("threadpoolctl", "statsmodels", "pandas-flavor", "tabulate", "xarray", "lazy_loader", "autograd",
           "numba", "llvmlite", "patsy", "future")


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


def pgmpy_version():
    v = version("pgmpy")
    if v != "unknown":
        return v
    import pgmpy
    return getattr(pgmpy, "__version__", "dev")


def main(outdir, quick, engines, rows, seed, out_name):
    outdir = Path(outdir)
    queries = json.loads((outdir / "queries.json").read_text())
    if engines is None:
        engines = [e for e in ENGINE_MODULES if importable(e)]
    missing = [e for e in engines if e not in ENGINE_MODULES or not importable(e)]
    if missing:
        sys.exit(f"engines not available in this interpreter: {missing}")
    unknown = [r for r in rows or [] if r not in ROWS]
    if unknown:
        sys.exit(f"unknown rows: {unknown}")
    dists = sorted({ENGINE_DISTS.get(e, e) for e in engines})
    versions = {d: (pgmpy_version() if d == "pgmpy" else version(d)) for d in dists}
    versions.update({"numpy": np.__version__, "pandas": pd.__version__,
                     "scipy": version("scipy"), "scikit-learn": version("scikit-learn")})
    helpers = {h: v for h in HELPERS if (v := version(h)) != "unknown"}
    meta = {
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cpu": cpu_name(),
        "logical_cpus": os.cpu_count(),
        "os": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),
        "engines": engines,
        "quick": quick,
        "passes": PASSES,
        "seed": seed,
        "uptime_start": sh("uptime"),
        "power": power_state(),
        "versions": versions,
        "helpers": helpers,
        "commits": {k: v for k, v in (("fastcit", fastcit_commit() if "fastcit" in engines else None),
                                      ("pgmpy", pgmpy_commit() if "pgmpy" in engines else None)) if v},
        "threads": thread_info(),
        "affinity": cpus_allowed(),
    }
    if rows:
        meta["rows"] = rows
    if "fastcit" in engines:
        meta["fastcit_trees"] = fastcit_trees()
    # The harness floor: a no-op engine on the discrete queries, through the same timing code.
    floor_qs = queries["discrete"]["queries"][: 2 if quick else None]
    floor = time_row({"noop": noop_engine}, None, floor_qs, random.Random(f"{seed}:floor"))["noop"]
    meta["harness_floor_ms"] = floor["median_ms"]
    print(f"harness floor: median {floor['median_ms']:.6f} ms", flush=True)
    results = {}
    cache = {}
    for row, (group, label, row_engines) in ROWS.items():
        todo = {e: f for e, f in row_engines.items() if e in engines}
        if not todo or (rows and row not in rows):
            continue
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
        results[row] = {"label": label, "engines": time_row(todo, cache[name], qs, random.Random(f"{seed}:{row}"))}
        for eng, res in results[row]["engines"].items():
            if (row, eng) in NOTES:
                res["note"] = NOTES[(row, eng)]
            print(f"{row:13s} {eng:16s} median {res['median_ms']} ms, total {res['total_ms']:.2f} ms ({len(qs)} q, {res['errors']} errors, {res['nan']} NaN)", flush=True)
    meta["uptime_end"] = sh("uptime")
    meta["power_end"] = power_state()
    (outdir / out_name).write_text(json.dumps({"meta": meta, "results": results}, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("outdir")
    ap.add_argument("--quick", action="store_true", help="use 2 queries per group")
    ap.add_argument("--engines", help="comma-separated engine names (default: all importable)")
    ap.add_argument("--rows", help="comma-separated row names, for example gcm (default: all rows)")
    ap.add_argument("--seed", type=int, default=1, help="seed of the engine order in each pass (default 1)")
    ap.add_argument("--out", default="python.json", help="file name inside OUTDIR (default python.json)")
    a = ap.parse_args()
    main(a.outdir, a.quick, a.engines.split(",") if a.engines else None, a.rows.split(",") if a.rows else None,
         a.seed, a.out)
