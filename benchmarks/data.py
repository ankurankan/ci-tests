"""Write the benchmark datasets and the shared query file.

Usage: python benchmarks/data.py OUTDIR

All data are synthetic and seeded. Running the script twice gives identical files.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def discrete(n=10_000, p=30, seed=0):
    """Random DAG, 2-4 levels per variable, random conditional probability tables."""
    rng = np.random.default_rng(seed)
    levels = rng.integers(2, 5, size=p)
    data = np.zeros((n, p), dtype=int)
    for j in range(p):
        k = int(rng.integers(0, 4)) if j else 0
        parents = sorted(rng.choice(j, size=min(k, j), replace=False)) if k else []
        cfg = np.zeros(n, dtype=int)
        for q in parents:
            cfg = cfg * levels[q] + data[:, q]
        n_cfg = int(np.prod([levels[q] for q in parents])) if parents else 1
        cpt = rng.dirichlet(np.full(levels[j], 0.7), size=n_cfg)
        cum = np.cumsum(cpt, axis=1)[cfg]
        data[:, j] = np.minimum((rng.random((n, 1)) > cum).sum(axis=1), levels[j] - 1)
    return pd.DataFrame(data, columns=[f"V{j}" for j in range(p)])


def gaussian(n=10_000, p=30, seed=0):
    """Linear Gaussian structural equation model on a random DAG."""
    rng = np.random.default_rng(seed)
    adj = np.triu(rng.random((p, p)) < 3.0 / (p - 1), k=1)
    w = rng.uniform(0.5, 1.5, (p, p)) * rng.choice([-1, 1], (p, p)) * adj
    x = np.zeros((n, p))
    for j in range(p):
        x[:, j] = x @ w[:, j] + rng.standard_normal(n)
    return pd.DataFrame(x, columns=[f"V{j}" for j in range(p)])


def nonlinear(n, seed):
    """Eight variables with tanh, sin, square and cos links."""
    rng = np.random.default_rng(seed)

    def e():
        return rng.standard_normal(n)

    a = e()
    b = np.tanh(a) + 0.5 * e()
    c = np.sin(b) + 0.5 * e()
    d = a**2 / 2 + 0.5 * e()
    ee = np.tanh(c) + d / 2 + 0.5 * e()
    f = np.cos(ee) + 0.5 * e()
    g = e()
    h = 0.7 * g + np.sin(a) + 0.5 * e()
    return pd.DataFrame(dict(A=a, B=b, C=c, D=d, E=ee, F=f, G=g, H=h))


def mixed(n=2000, seed=7):
    """Three categorical (D0-D2) and three continuous (C0-C2) variables."""
    rng = np.random.default_rng(seed)
    c0, c1 = rng.normal(size=n), rng.normal(size=n)
    c2 = 0.6 * c0 + 0.5 * c1 + rng.normal(size=n)
    d0 = np.digitize(c0 + 0.5 * rng.normal(size=n), [-0.5, 0.5])
    d1 = np.digitize(c1 + c2 * 0.5 + rng.normal(size=n), [-1, 0, 1])
    d2 = np.digitize(rng.normal(size=n) + 0.8 * d0, [0.5, 1.5])
    c1 = c1 + 0.4 * d2
    c2 = c2 + 0.3 * d1
    df = pd.DataFrame({"D0": d0, "D1": d1, "D2": d2, "C0": c0, "C1": c1, "C2": c2})
    for k in ("D0", "D1", "D2"):
        df[k] = "L" + df[k].astype(str)
    return df


def queries(cols, k, zmin, zmax, seed):
    """k distinct queries (x, y, z) with |z| between zmin and zmax."""
    rng = np.random.default_rng(seed)
    seen, out = set(), []
    while len(out) < k:
        nz = int(rng.integers(zmin, zmax + 1))
        pick = [str(c) for c in rng.choice(cols, 2 + nz, replace=False)]
        key = (frozenset(pick[:2]), frozenset(pick[2:]))
        if key not in seen:
            seen.add(key)
            out.append({"x": pick[0], "y": pick[1], "z": pick[2:]})
    return out


def main(outdir):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    frames = {
        "discrete.csv": discrete(),
        "gaussian.csv": gaussian(),
        "nonlin300.csv": nonlinear(300, 0),
        "nonlin1000.csv": nonlinear(1000, 1),
        "mixed.csv": mixed(),
    }
    for name, df in frames.items():
        df.to_csv(out / name, index=False)
    nl = list("ABCDEFGH")
    gcols = list(frames["gaussian.csv"].columns)
    q = {
        "discrete": {"data": "discrete.csv", "queries": queries(list(frames["discrete.csv"].columns), 50, 0, 3, 1)},
        "gaussian": {"data": "gaussian.csv", "queries": queries(gcols, 50, 0, 4, 2)},
        "hsic": {"data": "nonlin300.csv",
                 "queries": [{"x": a, "y": b, "z": []} for i, a in enumerate(nl) for b in nl[i + 1:]]},
        "kci": {"data": "nonlin300.csv", "queries": queries(nl, 30, 1, 2, 3)},
        "kci_1000": {"data": "nonlin1000.csv", "queries": queries(nl, 10, 1, 2, 4)},
        "gcm": {"data": "gaussian.csv", "queries": queries(gcols, 50, 0, 4, 5)},
        "pillai": {"data": "mixed.csv", "queries": queries(list(frames["mixed.csv"].columns), 40, 0, 2, 6)},
    }
    with open(out / "queries.json", "w") as f:
        json.dump(q, f, indent=1)
    print({k: len(v["queries"]) for k, v in q.items()})


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
