"""Write the sweep datasets and the sweep query file, and hold the sweep plan (grids per row).

Usage: python benchmarks/sweep_data.py OUTDIR [--max-n N]

One CSV per generator at the largest n of its sweep. A sweep point with n rows uses the first n rows of the file.
sweep-queries.json also holds "plan": the grids and, per row, the generator, the n grid, n_z and z_n. This plan is the
single source of the grids: sweep_python.py and sweep_r.R read it from the file and keep no copies.
sweep-queries.json holds, per generator, the data file and the queries for each conditioning-set size k in Z_GRID (0 to 8):
every query has exactly k conditioning variables, and all queries of one k are distinct.
--max-n caps the rows of every file (for tests). All data are synthetic and seeded. Running the script twice
gives identical files. The discrete and Gaussian generators come from benchmarks/data.py; its output does not change.
"""
import argparse
import json
from math import comb
from pathlib import Path

import numpy as np
import pandas as pd

import data as base

N_GRID = [100, 300, 1_000, 3_000, 10_000, 30_000, 100_000]
N_GRID_KERNEL = [100, 200, 500, 1_000, 2_000]
Z_GRID = [0, 1, 2, 3, 4, 6, 8]

# row -> generator, n grid of the n sweep, |Z| of the n sweep (n_z), n of the |Z| sweep (z_n).
# The n sweep uses |Z| = 1 (HSIC: Z empty). The |Z| sweep has no HSIC row.
PLAN = {
    **{row: {"gen": "discrete", "n_grid": N_GRID, "n_z": 1, "z_n": 10_000}
       for row in ("chi_square", "g_sq", "cressie_read", "freeman_tukey", "modified_ll")},
    **{row: {"gen": "gaussian", "n_grid": N_GRID, "n_z": 1, "z_n": 10_000}
       for row in ("fisher_z", "pearson_t", "pearson_equivalence", "gcm")},
    "pillai": {"gen": "mixed", "n_grid": N_GRID, "n_z": 1, "z_n": 2_000},
    "hsic": {"gen": "nonlinear", "n_grid": N_GRID_KERNEL, "n_z": 0, "z_n": None},
    "kci": {"gen": "nonlinear", "n_grid": N_GRID_KERNEL, "n_z": 1, "z_n": 500},
}
Z_ROWS = [row for row, plan in PLAN.items() if plan["z_n"]]
QUERIES = {"discrete": 20, "gaussian": 20, "mixed": 20, "nonlinear": 10}  # queries per point
QUERY_SEED = {"discrete": 11, "gaussian": 12, "mixed": 13, "nonlinear": 14}


def sweep_mixed(n, seed=7):
    """Six categorical (D0-D5) and six continuous (C0-C5) variables: enough for |Z| = 8 (10 columns) and 20 queries.

    This extends data.mixed (three of each), which stays unchanged.
    """
    rng = np.random.default_rng(seed)
    c0, c1, c3, c4, c5 = (rng.normal(size=n) for _ in range(5))
    c2 = 0.6 * c0 + 0.5 * c1 + rng.normal(size=n)
    d0 = np.digitize(c0 + 0.5 * rng.normal(size=n), [-0.5, 0.5])
    d1 = np.digitize(c1 + c2 * 0.5 + rng.normal(size=n), [-1, 0, 1])
    d2 = np.digitize(rng.normal(size=n) + 0.8 * d0, [0.5, 1.5])
    d3 = np.digitize(c3 + 0.5 * rng.normal(size=n), [0.0])
    d4 = np.digitize(c4 + 0.4 * d1 + 0.5 * rng.normal(size=n), [-0.5, 0.5])
    d5 = np.digitize(rng.normal(size=n) + 0.6 * d3, [0.3, 1.0])
    c1 = c1 + 0.4 * d2
    c2 = c2 + 0.3 * d1
    c3 = c3 + 0.3 * d0
    c4 = c4 + 0.3 * d5
    c5 = 0.5 * c4 + c5
    df = pd.DataFrame({"D0": d0, "D1": d1, "D2": d2, "D3": d3, "D4": d4, "D5": d5,
                       "C0": c0, "C1": c1, "C2": c2, "C3": c3, "C4": c4, "C5": c5})
    for k in ("D0", "D1", "D2", "D3", "D4", "D5"):
        df[k] = "L" + df[k].astype(str)
    return df


def sweep_nonlinear(n, seed=0):
    """Twelve variables (V0-V11) with tanh, sin, square and cos links plus noise.

    The style of data.nonlinear (eight variables, which stays unchanged). V6 and V9 start new chains, so the
    data have independent pairs (for example V0 and V6) and dependent pairs.
    """
    rng = np.random.default_rng(seed)

    def e():
        return rng.standard_normal(n)

    v0 = e()
    v1 = np.tanh(v0) + 0.5 * e()
    v2 = np.sin(v1) + 0.5 * e()
    v3 = v0**2 / 2 + 0.5 * e()
    v4 = np.tanh(v2) + v3 / 2 + 0.5 * e()
    v5 = np.cos(v4) + 0.5 * e()
    v6 = e()
    v7 = 0.7 * v6 + np.sin(v0) + 0.5 * e()
    v8 = np.cos(v6) + 0.5 * e()
    v9 = e()
    v10 = np.tanh(v9) + v8**2 / 2 + 0.5 * e()
    v11 = np.sin(v10) + 0.5 * v5 + 0.5 * e()
    cols = [v0, v1, v2, v3, v4, v5, v6, v7, v8, v9, v10, v11]
    return pd.DataFrame({f"V{i}": v for i, v in enumerate(cols)})


def sweep_queries(cols, count, k, seed):
    """count distinct queries with |Z| = k. Stops with an error when the columns allow fewer (no endless loop)."""
    possible = comb(len(cols), 2) * comb(len(cols) - 2, k)
    if len(cols) < 2 + k or possible < count:
        raise ValueError(f"{len(cols)} columns allow {max(possible, 0)} queries with |Z| = {k}; {count} are needed")
    return base.queries(cols, count, k, k, seed)


def max_rows(gen):
    return max(max(p["n_grid"] + [p["z_n"] or 0]) for p in PLAN.values() if p["gen"] == gen)


def main(outdir, max_n=None):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    rows = {g: min(max_rows(g), max_n or max_rows(g)) for g in QUERIES}
    frames = {
        "discrete": base.discrete(rows["discrete"], p=30),
        "gaussian": base.gaussian(rows["gaussian"], p=30),
        "nonlinear": sweep_nonlinear(rows["nonlinear"]),
        "mixed": sweep_mixed(rows["mixed"]),
    }
    spec = {"plan": {"grids": {"n": N_GRID, "n_kernel": N_GRID_KERNEL, "z": Z_GRID}, "rows": PLAN}}
    for gen, df in frames.items():
        name = f"sweep-{gen}.csv"
        df.to_csv(out / name, index=False)
        cols = list(df.columns)
        spec[gen] = {"data": name, "rows": len(df), "queries": {
            str(k): sweep_queries(cols, QUERIES[gen], k, QUERY_SEED[gen] * 10 + k) for k in Z_GRID}}
    (out / "sweep-queries.json").write_text(json.dumps(spec, indent=1))
    print({g: (spec[g]["rows"], QUERIES[g]) for g in frames})


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("outdir")
    ap.add_argument("--max-n", type=int, help="cap the rows of every file (for tests)")
    a = ap.parse_args()
    main(a.outdir, a.max_n)
