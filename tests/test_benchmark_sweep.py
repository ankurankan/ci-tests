"""Tests of the sweep data generator and the Python sweep harness (no benchmark package needed)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

BENCH = Path(__file__).resolve().parents[1] / "benchmarks"
sys.path.insert(0, str(BENCH))

import sweep_data  # noqa: E402


@pytest.fixture(scope="module")
def small(tmp_path_factory):
    out = tmp_path_factory.mktemp("sweep")
    sweep_data.main(out, max_n=300)
    return out


def test_grids_match_the_plan():
    grid = [100, 300, 1000, 3000, 10000, 30000, 100000]
    assert sweep_data.N_GRID == grid
    assert not hasattr(sweep_data, "N_GRID_KERNEL")  # one n grid for every row, the kernel rows too
    assert sweep_data.Z_GRID == [0, 1, 2, 3, 4, 6, 8]
    for row, plan in sweep_data.PLAN.items():
        assert plan["n_grid"] == grid, row
        assert plan["z_n"] == (None if row == "hsic" else 1000), row  # the |Z| sweep runs at n = 1 000 in every row
        assert plan["n_max"] == (10000 if row in ("hsic", "kci") else None), row  # n x n matrices: memory limit
    assert "hsic" not in sweep_data.Z_ROWS
    assert sweep_data.PLAN["hsic"]["n_z"] == 0 and sweep_data.PLAN["kci"]["n_z"] == 1


def test_written_plan_matches_the_constraints(small):
    plan = json.loads((small / "sweep-queries.json").read_text())["plan"]
    grid = [100, 300, 1000, 3000, 10000, 30000, 100000]
    assert plan["grids"] == {"n": grid, "z": [0, 1, 2, 3, 4, 6, 8]}
    assert set(plan["rows"]) == {"chi_square", "g_sq", "cressie_read", "freeman_tukey", "modified_ll", "fisher_z",
                                 "pearson_t", "pearson_equivalence", "gcm", "pillai", "hsic", "kci"}
    for row, p in plan["rows"].items():
        assert set(p) == {"gen", "n_grid", "n_z", "z_n", "n_max"}
        assert p["n_grid"] == grid, row
        assert p["z_n"] == (None if row == "hsic" else 1000), row
        assert p["n_max"] == (10000 if row in ("hsic", "kci") else None), row
        assert p["n_z"] == (0 if row == "hsic" else 1), row
        assert p["gen"] == {"pillai": "mixed", "hsic": "nonlinear", "kci": "nonlinear"}.get(
            row, "discrete" if row in ("chi_square", "g_sq", "cressie_read", "freeman_tukey", "modified_ll")
            else "gaussian"), row


def test_data_is_deterministic(small, tmp_path):
    sweep_data.main(tmp_path, max_n=300)
    names = sorted(p.name for p in small.iterdir())
    assert names == sorted(p.name for p in tmp_path.iterdir())
    assert "sweep-queries.json" in names
    for name in names:
        assert (small / name).read_bytes() == (tmp_path / name).read_bytes(), name


def test_row_counts(small):
    import pandas as pd
    q = json.loads((small / "sweep-queries.json").read_text())
    q.pop("plan")
    for gen, spec in q.items():
        assert len(pd.read_csv(small / spec["data"])) == 300, gen


def test_queries_have_exact_k_and_are_distinct(small):
    q = json.loads((small / "sweep-queries.json").read_text())
    q.pop("plan")
    assert set(q) == {"discrete", "gaussian", "nonlinear", "mixed"}
    import pandas as pd
    for gen, spec in q.items():
        cols = set(pd.read_csv(small / spec["data"]).columns)
        want = 10 if gen == "nonlinear" else 20
        assert sorted(spec["queries"], key=int) == ["0", "1", "2", "3", "4", "6", "8"]
        for k, qs in spec["queries"].items():
            assert len(qs) == want, (gen, k)
            seen = set()
            for item in qs:
                assert len(item["z"]) == int(k)
                variables = [item["x"], item["y"], *item["z"]]
                assert len(set(variables)) == 2 + int(k)
                assert set(variables) <= cols
                key = (item["x"], item["y"], tuple(sorted(item["z"])))
                assert key not in seen
                seen.add(key)


def test_mixed_has_enough_columns():
    df = sweep_data.sweep_mixed(50)
    assert sum(c.startswith("D") for c in df.columns) >= 6
    assert sum(c.startswith("C") for c in df.columns) >= 6
    assert all(str(v).startswith("L") for c in df.columns if c.startswith("D") for v in df[c])


def test_nonlinear_has_enough_columns_and_no_categorical_names():
    import re
    df = sweep_data.sweep_nonlinear(50)
    assert df.shape == (50, 12)
    assert not any(re.fullmatch(r"D\d", c) for c in df.columns)


def test_query_sampler_stops_when_too_few_queries_exist():
    with pytest.raises(ValueError):
        sweep_data.sweep_queries(["a", "b", "c"], 20, 1, 1)
    assert len(sweep_data.sweep_queries([f"V{i}" for i in range(12)], 10, 8, 1)) == 10


def test_every_row_has_a_plan():
    import sweep_python
    assert set(sweep_python.ROWS) == set(sweep_data.PLAN)  # the written plan has the same rows (tested above)


def _engines():
    def good(data):
        return lambda q: (1.0, 0.5)

    def flaky(data):
        def run(q):
            if q["x"] == "bad":
                raise ValueError("boom")
            return 1.0, float("nan") if q["x"] == "nan" else 0.5
        return run

    def broken(data):
        raise RuntimeError("cannot build")

    return {"good": good, "flaky": flaky, "broken": broken}


QS = [{"x": "a", "y": "b", "z": []}, {"x": "bad", "y": "b", "z": []}, {"x": "nan", "y": "b", "z": []}]


def test_sweep_runs_one_pass():
    import sweep_python
    assert sweep_python.PASSES == 1


def _state(times_s, err=(), nan=()):
    """The state of bench_python.time_pass after one pass with these call times (in seconds)."""
    n = len(times_s)
    return {"times": [[t] for t in times_s], "err": [i in err for i in range(n)], "nan": [i in nan for i in range(n)],
            "totals": [0.5 + sum(times_s)], "setups": [0.5]}


def test_point_stats_leave_out_the_first_call():
    import sweep_python
    st = sweep_python.point_stats(_state([0.010, 0.002, 0.004, 0.006]))  # the first call does the one-time work
    assert st["first_ms"] == pytest.approx(10.0)
    assert st["mean_ms"] == pytest.approx(4.0) and st["n_timed"] == 3
    assert st["sd_ms"] == pytest.approx(2.0) and st["se_ms"] == pytest.approx(2.0 / 3 ** 0.5)
    assert st["ms"] == pytest.approx([10.0, 2.0, 4.0, 6.0])  # every call stays in the run file
    assert st["setup_ms"] == pytest.approx(500.0) and st["total_ms"] == pytest.approx(522.0)


def test_point_stats_leave_out_errors_and_nan():
    import sweep_python
    st = sweep_python.point_stats(_state([0.010, 0.002, 0.050, 0.004, 0.006], err={2}, nan={4}))
    assert st["mean_ms"] == pytest.approx(3.0) and st["n_timed"] == 2
    assert (st["errors"], st["nan"], st["n_queries"]) == (1, 1, 5)
    assert st["ms"][2] is None and st["ms"][4] is None


def test_point_stats_with_too_few_calls():
    import sweep_python
    one = sweep_python.point_stats(_state([0.010, 0.002]))  # a quick run: one call after the warm-up call
    assert one["mean_ms"] == pytest.approx(2.0) and one["sd_ms"] is None and one["se_ms"] is None
    none = sweep_python.point_stats(_state([0.010, 0.002], nan={1}))
    assert none["mean_ms"] is None and none["n_timed"] == 0 and none["first_ms"] == pytest.approx(10.0)


def test_time_point_counts_errors_and_nan_as_missing():
    import random
    import sweep_python
    res, over = sweep_python.time_point(_engines(), None, QS, random.Random(1), 1)
    assert over == set()
    assert res["good"]["errors"] == 0 and res["good"]["n_timed"] == 2 and res["good"]["passes"] == 1
    assert res["good"]["mean_ms"] is not None and res["good"]["first_ms"] is not None
    f = res["flaky"]  # the calls after the warm-up call: one error and one NaN
    assert (f["errors"], f["nan"], f["n_timed"]) == (1, 1, 0) and f["mean_ms"] is None
    assert f["ms"][0] is not None and f["ms"][1] is None and f["ms"][2] is None
    assert res["broken"]["mean_ms"] is None and "cannot build" in res["broken"]["error"]


def test_time_point_budget_stops_remaining_passes():
    import random
    import sweep_python
    res, over = sweep_python.time_point({"good": _engines()["good"]}, None, QS, random.Random(1), 3, budget=-1)
    assert over == {"good"} and res["good"]["passes"] == 1 and res["good"]["mean_ms"] is not None


def test_run_file_shape_and_budget_skip(small, monkeypatch):
    import sweep_python
    from sweep_python import bp
    monkeypatch.setattr(bp, "importable", lambda e: True)
    for name in _engines():
        monkeypatch.setitem(bp.ENGINE_MODULES, name, "x")
    queries = small / "sweep-queries.json"
    spec = json.loads(queries.read_text())
    spec["plan"]["rows"]["fisher_z"]["z_n"] = 200
    queries.write_text(json.dumps(spec))
    monkeypatch.setattr(sweep_python, "ROWS", {"fisher_z": ("Fisher-z", _engines())})
    monkeypatch.setattr(sweep_python, "BUDGET_S", -1)  # every first pass is over budget
    sweep_python.main(small, False, ["good", "flaky", "broken"], None, ["n", "z"], 1, "run.json")
    run = json.loads((small / "run.json").read_text())
    assert {"date", "cpu", "versions", "power", "harness_floor_ms", "passes"} <= set(run["meta"])
    sw = run["results"]["fisher_z"]["sweeps"]
    assert sw["n"]["x"] == [100, 300] and sw["n"]["fixed"] == {"z": 1}
    assert sw["z"]["x"] == [0, 1, 2, 3, 4, 6, 8] and sw["z"]["fixed"] == {"n": 200}
    assert len(sw["z"]["engines"]["good"][0]["ms"]) == 20
    good = sw["n"]["engines"]["good"]
    assert good[0]["skipped"] is None and good[0]["passes"] == 1
    assert good[1]["skipped"] == "time budget" and good[1]["mean_ms"] is None
    assert set(good[0]) >= {"mean_ms", "sd_ms", "se_ms", "first_ms", "setup_ms", "total_ms", "ms", "errors", "nan",
                            "n_queries", "n_timed", "skipped"}
    assert "median_ms" not in good[0]


def _run_with_n_max(small, tmp_path, monkeypatch, budget=None):
    """Run the n sweep of one row whose plan stops at n = 100 (the data have the points 100 and 300)."""
    import sweep_python
    from sweep_python import bp
    seen = []

    def counting(data):
        seen.append(len(data["df"]))  # the rows of each engine pass
        return lambda q: (1.0, 0.5)

    out = tmp_path / "sweep"
    shutil.copytree(small, out)
    spec = json.loads((out / "sweep-queries.json").read_text())
    spec["plan"]["rows"]["fisher_z"]["n_max"] = 100
    (out / "sweep-queries.json").write_text(json.dumps(spec))
    monkeypatch.setattr(bp, "importable", lambda e: True)
    monkeypatch.setitem(bp.ENGINE_MODULES, "good", "x")
    monkeypatch.setattr(sweep_python, "ROWS", {"fisher_z": ("Fisher-z", {"good": counting})})
    if budget is not None:
        monkeypatch.setattr(sweep_python, "BUDGET_S", budget)
    sweep_python.main(out, False, ["good"], None, ["n"], 1, "run.json")
    sweep = json.loads((out / "run.json").read_text())["results"]["fisher_z"]["sweeps"]["n"]
    return sweep, seen


def test_points_above_n_max_are_skipped_for_memory(small, tmp_path, monkeypatch):
    sweep, seen = _run_with_n_max(small, tmp_path, monkeypatch)
    assert sweep["x"] == [100, 300]  # the point stays on the axis
    first, second = sweep["engines"]["good"]
    assert first["skipped"] is None and first["mean_ms"] is not None and first["passes"] == 1
    assert first["n_timed"] == 19  # 20 queries without the warm-up call
    assert second["skipped"] == "memory limit" and second["mean_ms"] is None and second["passes"] == 0
    assert second["n_queries"] == 20
    assert seen == [100]  # one pass, and no engine pass with 300 rows


def test_an_engine_over_the_time_budget_keeps_that_reason_above_n_max(small, tmp_path, monkeypatch):
    sweep, seen = _run_with_n_max(small, tmp_path, monkeypatch, budget=-1)  # the first pass is over budget
    assert [p["skipped"] for p in sweep["engines"]["good"]] == [None, "time budget"]
    assert seen == [100]


def test_only_mixed_data_gets_categorical_columns(small):
    import sweep_python
    spec = json.loads((small / "sweep-queries.json").read_text())
    for gen, want in (("nonlinear", False), ("mixed", True), ("discrete", False)):
        df = sweep_python.load_frames(small, spec[gen])["df"]
        assert any(str(t) == "category" for t in df.dtypes) == want, gen


# ---- summarize_sweep.py -------------------------------------------------------------------------------------------

import shutil  # noqa: E402

import summarize_sweep  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sweep"


@pytest.fixture(scope="module")
def summary(tmp_path_factory):
    out = tmp_path_factory.mktemp("summary")
    for f in FIXTURE.glob("*.json"):
        shutil.copy(f, out / f.name)
    summarize_sweep.main(out)
    return out, json.loads((out / "sweep.json").read_text()), (out / "sweep.md").read_text()


def series(data, lang, row, axis):
    language = next(x for x in data["languages"] if x["key"] == lang)
    r = next(x for x in language["rows"] if x["key"] == row)
    return r["sweeps"][axis], {s["engine"]: s for s in r["sweeps"][axis]["series"]}


def test_schema(summary):
    _, data, _ = summary
    assert set(data) >= {"meta", "languages"}
    assert [x["key"] for x in data["languages"]] == ["python", "r"]
    assert set(data["meta"]) == {"python", "r"}
    for key in ("date", "cpu", "os", "interpreter", "versions", "passes", "budget_s"):
        assert key in data["meta"]["python"], key
    assert data["meta"]["python"]["interpreter"] == "Python 3.14.2"
    for language in data["languages"]:
        assert language["label"]
        for row in language["rows"]:
            assert row["label"]
            for axis, sweep in row["sweeps"].items():
                assert axis in ("n", "z")
                assert set(sweep) >= {"fixed", "x", "series"}
                for s in sweep["series"]:
                    assert set(s) >= {"engine", "label", "values", "skipped", "notes"}
                    assert len(s["values"]) == len(s["skipped"]) == len(sweep["x"])
                    assert isinstance(s["notes"], list)
    json.dumps(data, allow_nan=False)  # no NaN in the output


def test_rows_and_axes(summary):
    _, data, _ = summary
    py = next(x for x in data["languages"] if x["key"] == "python")
    assert [r["key"] for r in py["rows"]] == ["chi_square", "gcm", "pillai"]  # the order of the existing summary
    sweep, _ = series(data, "python", "chi_square", "z")
    assert sweep["fixed"] == {"n": 10000} and sweep["x"] == [0, 1]
    sweep, _ = series(data, "python", "chi_square", "n")
    assert sweep["fixed"] == {"z": 1} and sweep["x"] == [100, 300, 1000]
    assert "z" not in next(r for r in py["rows"] if r["key"] == "gcm")["sweeps"]


def test_fastcit_first_and_fixed_order(summary):
    _, data, _ = summary
    for lang, row in (("python", "chi_square"), ("python", "gcm"), ("r", "g_sq")):
        _, s = series(data, lang, row, "n")
        assert list(s)[0] == "fastcit"
    _, s = series(data, "python", "chi_square", "n")
    assert list(s) == ["fastcit", "pgmpy", "pingouin"]  # "fastcit (yates)" is dropped
    _, s = series(data, "r", "g_sq", "n")
    assert list(s) == ["fastcit", "pcalg", "bnlearn"]  # the order of the existing R table, not of the file
    assert s["fastcit"]["label"] == "FastCIT"


def test_missing_points_are_null_with_a_reason(summary):
    _, data, _ = summary
    _, s = series(data, "python", "chi_square", "n")
    assert s["pgmpy"]["values"] == [1.5, 2.5, None]
    assert s["pgmpy"]["skipped"] == [None, None, "time budget"]
    assert s["pingouin"]["values"][:2] == [None, None]
    assert s["pingouin"]["skipped"][0].startswith("error") and "boom" in s["pingouin"]["skipped"][0]
    assert s["pingouin"]["skipped"][1] == "all queries NaN"
    assert s["pingouin"]["values"][2] == 3.0 and s["pingouin"]["skipped"][2] is None
    assert s["pingouin"]["excluded"] == [1, 1, 1]
    assert 0 not in [v for x in s.values() for v in x["values"] if v is None]  # null stays null, never 0


def test_one_pass_point_keeps_its_value_and_is_marked(summary):
    _, data, md = summary
    _, s = series(data, "python", "pillai", "n")
    assert s["pgmpy"]["values"][2] == 61000.0 and s["pgmpy"]["skipped"][2] is None
    assert s["pgmpy"]["passes"] == [3, 3, 1]
    assert "61 000†" in md


def test_notes_are_engine_level(summary):
    _, data, _ = summary
    _, s = series(data, "python", "pillai", "n")
    assert len(s["pgmpy"]["notes"]) == 1 and "random forest" in s["pgmpy"]["notes"][0]
    assert s["fastcit"]["notes"] == []
    _, s = series(data, "r", "g_sq", "n")
    assert any("n < 10" in n for n in s["pcalg"]["notes"])
    _, s = series(data, "python", "chi_square", "n")  # the Yates note of the existing summary
    assert any("Yates" in n for n in s["pgmpy"]["notes"])


def test_dowhy_is_a_series_and_fastcit_reference_is_meta(summary):
    _, data, _ = summary
    _, s = series(data, "python", "gcm", "n")
    assert list(s) == ["fastcit", "pgmpy", "dowhy"]
    assert s["dowhy"]["values"] == [40.0, 41.0, 45.0]
    assert s["fastcit"]["values"] == [1.0, 1.1, 1.2]  # the reference does not replace it
    other = data["meta"]["python"]["other_runs"]
    assert len(other) == 1 and other[0]["interpreter"] == "Python 3.11.9"
    assert other[0]["reference"]["gcm"]["n"]["values"] == [1.05, 1.15, 1.25]


def test_markdown_has_one_table_per_language_test_axis(summary):
    _, data, md = summary
    expected = sum(len(r["sweeps"]) for lang in data["languages"] for r in lang["rows"])
    assert expected == 5  # python: chi_square n+z, gcm n, pillai n; r: g_sq n
    assert md.count("\n|---|") == expected
    assert "### Python, χ², sample size (|Z| = 1)" in md
    assert "### Python, χ², conditioning-set size (n = 10 000)" in md
    assert "### R, G², sample size (|Z| = 1)" in md
    assert "| FastCIT | 0.010 | 0.020 | 0.050 |" in md
    assert "1 000" in md  # x values use the number format of the existing summary
    assert "—‡" in md  # time budget, with a footnote
    assert "—§" in md  # error or NaN, with a footnote
    assert "fastcit (yates)" not in md


def test_values_are_means_with_their_spread(summary):
    _, data, md = summary
    _, s = series(data, "python", "gcm", "n")
    assert s["fastcit"]["values"] == [1.0, 1.1, 1.2]
    assert s["fastcit"]["sd"] == [0.2, 0.22, 0.24]  # the standard deviation over the calls
    assert s["fastcit"]["se"] == pytest.approx([0.05, 0.055, 0.06])  # the standard error of the mean
    assert s["fastcit"]["first_ms"] == [9.0, 9.0, 9.0]  # the warm-up call, not part of the mean
    assert s["pgmpy"]["sd"] == [None] * 3 and s["pgmpy"]["se"] == [None] * 3  # the run file has no spread
    assert "first_ms" not in s["pgmpy"]
    assert "| FastCIT | 1.00 ± 0.200 | 1.10 ± 0.220 | 1.20 ± 0.240 |" in md  # mean ± standard deviation
    assert "| pgmpy dev | 5.00 | 6.00 | 7.00 |" in md


def test_markdown_header_names_the_method(summary):
    _, _, md = summary
    head = md.split("\n## ", 1)[0]
    assert "mean time of one test call" in head and "median" not in head
    assert "standard deviation" in head and "first call" in head


def test_markdown_header_sentences_are_short(summary):
    _, _, md = summary
    head = md.split("\n## ", 1)[0]
    import re
    for sentence in re.split(r"(?<=[.!?])\s+", " ".join(head.splitlines()[1:])):
        assert len(sentence.split()) <= 25, sentence


def test_missing_run_file_for_a_language_is_skipped(tmp_path):
    shutil.copy(FIXTURE / "sweep-r.json", tmp_path / "sweep-r.json")
    summarize_sweep.main(tmp_path)
    data = json.loads((tmp_path / "sweep.json").read_text())
    assert [x["key"] for x in data["languages"]] == ["r"]


# ---- review fixes: setup note, mostly-NaN points, small values, setup_ms ----------------------------------------------


def _pt(mean, nan=0, n=20, **kw):
    return {"mean_ms": mean, "ms": None, "errors": 0, "nan": nan, "n_queries": n, "n_timed": n - nan,
            "passes": 3, "skipped": None, "error": None, **kw}


@pytest.fixture(scope="module")
def edge(tmp_path_factory):
    out = tmp_path_factory.mktemp("edge")
    pts = {"fastcit": [_pt(0.00043, setup_ms=0.1, total_ms=0.2), _pt(0.00044, setup_ms=0.1, total_ms=0.2),
                       _pt(0.0014, setup_ms=0.1, total_ms=0.2)],
           "pgmpy": [_pt(5.0, nan=12), _pt(6.0, nan=3), _pt(7.0, nan=10)]}
    run = {"meta": {"kind": "sweep", "python": "3.14.2", "passes": 3, "time_budget_s": 60.0, "quick": False,
                    "engines": ["fastcit", "pgmpy"]},
           "results": {r: {"label": r, "sweeps": {"n": {"fixed": {"z": 1}, "x": [100, 300, 1000], "engines": pts}}}
                       for r in ("fisher_z", "chi_square")}}
    (out / "sweep-python.json").write_text(json.dumps(run))
    summarize_sweep.main(out)
    return json.loads((out / "sweep.json").read_text()), (out / "sweep.md").read_text()


def test_fewer_than_half_of_the_queries_make_the_point_null(edge):
    data, md = edge
    _, s = series(data, "python", "fisher_z", "n")
    assert s["pgmpy"]["values"] == [None, 6.0, 7.0]  # 12 of 20 NaN: null; 3 of 20: kept; 10 of 20: kept (half)
    assert s["pgmpy"]["skipped"][0] == "12 of 20 queries gave NaN or an error"
    assert s["pgmpy"]["excluded"] == [12, 3, 10] and s["pgmpy"]["queries"] == [20, 20, 20]
    assert "at 300: 3 of 20 queries left out" in md
    assert "at 100: 12 of 20 queries gave NaN or an error" in md


def test_setup_note_is_on_the_rows_with_a_precomputed_matrix(edge):
    data, md = edge
    _, s = series(data, "python", "fisher_z", "n")
    assert any("one-time setup" in n for n in s["fastcit"]["notes"])
    _, s = series(data, "python", "chi_square", "n")
    assert not any("one-time setup" in n for n in s["fastcit"]["notes"])
    assert "one-time setup" in md


def test_setup_and_total_times_are_carried(edge):
    data, _ = edge
    _, s = series(data, "python", "fisher_z", "n")
    assert s["fastcit"]["setup_ms"] == [0.1] * 3 and s["fastcit"]["total_ms"] == [0.2] * 3
    assert "setup_ms" not in s["pgmpy"]  # the run file has none


def test_small_values_keep_two_significant_digits(edge):
    _, md = edge
    assert "| FastCIT | 0.00043 | 0.00044 | 0.0014 |" in md
    assert summarize_sweep.sfmt(0.5) == "0.500" and summarize_sweep.sfmt(12.34) == "12.3"


def test_memory_limit_points_have_their_own_mark(tmp_path):
    skipped = {"mean_ms": None, "ms": None, "errors": 0, "nan": 0, "n_queries": 10, "n_timed": 0, "passes": 0,
               "skipped": "memory limit", "error": None}
    budget = {**skipped, "skipped": "time budget"}
    pts = {"fastcit": [_pt(70.0, n=10), skipped], "hyppo": [_pt(200.0, n=10), budget]}
    run = {"meta": {"kind": "sweep", "python": "3.14.2", "passes": 3, "time_budget_s": 60.0, "quick": False,
                    "engines": ["fastcit", "hyppo"]},
           "results": {"hsic": {"label": "HSIC", "sweeps": {"n": {"fixed": {"z": 0}, "x": [10000, 30000],
                                                                  "engines": pts}}}}}
    (tmp_path / "sweep-python.json").write_text(json.dumps(run))
    summarize_sweep.main(tmp_path)
    data, md = json.loads((tmp_path / "sweep.json").read_text()), (tmp_path / "sweep.md").read_text()
    _, s = series(data, "python", "hsic", "n")
    assert s["fastcit"]["values"] == [70.0, None] and s["fastcit"]["skipped"] == [None, "memory limit"]
    assert "| FastCIT | 70.0 | —¶ |" in md
    assert "| 200 | —‡ |" in md  # hyppo: the time budget keeps its own mark
    notes = [line for line in md.splitlines() if line.startswith("- ¶")]
    assert len(notes) == 1 and "memory" in notes[0]
    assert "—§" not in md  # not counted as a failed point
