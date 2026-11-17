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
    big = [100, 300, 1000, 3000, 10000, 30000, 100000]
    kernel = [100, 200, 500, 1000, 2000]
    assert sweep_data.N_GRID == big
    assert sweep_data.N_GRID_KERNEL == kernel
    assert sweep_data.Z_GRID == [0, 1, 2, 3, 4]
    for row, plan in sweep_data.PLAN.items():
        assert plan["n_grid"] == (kernel if row in ("hsic", "kci") else big), row
        assert plan["z_n"] == {"pillai": 2000, "kci": 500, "hsic": None}.get(row, 10000), row
    assert "hsic" not in sweep_data.Z_ROWS
    assert sweep_data.PLAN["hsic"]["n_z"] == 0 and sweep_data.PLAN["kci"]["n_z"] == 1


def test_written_plan_matches_the_constraints(small):
    plan = json.loads((small / "sweep-queries.json").read_text())["plan"]
    big = [100, 300, 1000, 3000, 10000, 30000, 100000]
    kernel = [100, 200, 500, 1000, 2000]
    assert plan["grids"] == {"n": big, "n_kernel": kernel, "z": [0, 1, 2, 3, 4]}
    assert set(plan["rows"]) == {"chi_square", "g_sq", "cressie_read", "freeman_tukey", "modified_ll", "fisher_z",
                                 "pearson_t", "pearson_equivalence", "gcm", "pillai", "hsic", "kci"}
    for row, p in plan["rows"].items():
        assert set(p) == {"gen", "n_grid", "n_z", "z_n"}
        assert p["n_grid"] == (kernel if row in ("hsic", "kci") else big), row
        assert p["z_n"] == {"pillai": 2000, "kci": 500, "hsic": None}.get(row, 10000), row
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
        assert sorted(spec["queries"], key=int) == ["0", "1", "2", "3", "4"]
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
    assert sum(c.startswith("D") for c in df.columns) >= 4
    assert sum(c.startswith("C") for c in df.columns) >= 4


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


def test_time_point_counts_errors_and_nan_as_missing():
    import random
    import sweep_python
    res, over = sweep_python.time_point(_engines(), None, QS, random.Random(1), 2)
    assert over == set()
    assert res["good"]["errors"] == 0 and res["good"]["n_timed"] == 3 and res["good"]["passes"] == 2
    f = res["flaky"]
    assert (f["errors"], f["nan"], f["n_timed"]) == (1, 1, 1)
    assert f["ms"][0] is not None and f["ms"][1] is None and f["ms"][2] is None
    assert res["broken"]["median_ms"] is None and "cannot build" in res["broken"]["error"]


def test_time_point_budget_stops_remaining_passes():
    import random
    import sweep_python
    res, over = sweep_python.time_point({"good": _engines()["good"]}, None, QS, random.Random(1), 3, budget=-1)
    assert over == {"good"} and res["good"]["passes"] == 1 and res["good"]["median_ms"] is not None


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
    assert sw["z"]["x"] == [0, 1, 2, 3, 4] and sw["z"]["fixed"] == {"n": 200}
    assert len(sw["z"]["engines"]["good"][0]["ms"]) == 20
    good = sw["n"]["engines"]["good"]
    assert good[0]["skipped"] is None and good[0]["passes"] == 1
    assert good[1]["skipped"] == "time budget" and good[1]["median_ms"] is None
    assert set(good[0]) >= {"median_ms", "ms", "errors", "nan", "n_queries", "skipped"}


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
    assert any("n < 5" in n for n in s["pcalg"]["notes"])
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
