# README Rewrite and Performance Comparison Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reproducible cross-package benchmark (`benchmarks/`) and rewrite the root README in ASD-STE100 with a two-column test table, released-package install steps, per-language collapsible examples and a performance section.

**Architecture:** Seeded synthetic data and queries feed one Python and one R timing script; a summarizer turns their JSON results into Markdown tables that the README quotes.

**Tech Stack:** Python (numpy, pandas, scipy), R (conda env `cir-dev`), FastCIT wheel/R package built from this branch.

**Spec:** `docs/superpowers/specs/2026-11-16-readme-benchmarks-design.md`

## Global Constraints

- Branch `feature/readme-benchmarks` (off `feature/rename-fastcit`). Commit locally; never push. Every commit message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Package names: Python `fastcit` (`import fastcit`), npm `fastcit`, R `fastcit`, Rust `fastcit-core` (`use fastcit_core`). Brand "FastCIT", tagline "FastCIT: Fast Conditional Independence Tests".
- pgmpy reference: `dev` at commit `a67c17d9` (from `git -C /home/ankur/work/pgmpy/pgmpy archive a67c17d9`), never `feature/optimization`. Comparison versions: causal-learn 0.1.4.5, andrey-core 0.17.1, pcalg 2.7.12, bnlearn 5.2.1, dHSIC 2.2.
- Timing: 3 passes per engine; new test objects each pass (construction not timed; caches off where an option exists); each query timed once per pass; per-query best of 3; median in ms. χ²/G² without Yates in every package.
- No library code changes. Binding READMEs unchanged. Never install into the active `pgmpy` conda env; use scratchpad `--target` dirs and `PYTHONPATH` (scratchpad: `/tmp/claude-1000/-home-ankur-work-pgmpy-ci-tests/1caf9050-6f9c-4107-a19b-c282dc5333a9/scratchpad`). R work in conda env `cir-dev` (`LD_LIBRARY_PATH=$CONDA_PREFIX/lib/R/lib:$CONDA_PREFIX/lib`).
- README: ASD-STE100 — instructions ≤ 20 words, descriptions ≤ 25 words, active voice, imperative instructions, one instruction per sentence, simple words, no idioms.

## Review Focus

1. **Every README code snippet runs as written** against the packages built from this branch (Python wheel, JS `pkg/`, installed R package, Rust via `cargo test` of a doc example or a scratch crate) — Task 2 verification.
2. **Benchmark fairness**: identical data and queries for every engine, construction excluded, caches off, same statistic definitions; a package that computes a different statistic (e.g. pgmpy's random-forest Pillai) is labelled as such — Task 1 review.
3. **Reproducibility**: the scripts take no hard-coded scratchpad paths; `benchmarks/README.md` lists exact install commands and versions; results record date, CPU, OS, versions, commit hashes — Task 1.
4. **Table accuracy**: README numbers equal `benchmarks/results/summary.md` — Task 2.
5. **STE compliance** of README sentences (length, voice, one instruction each) — Task 2 review.

---

### Task 1: Reproducible benchmark

**Files:** Create `benchmarks/data.py`, `benchmarks/bench_python.py`, `benchmarks/bench_r.R`, `benchmarks/summarize.py`, `benchmarks/README.md`, `benchmarks/results/python.json`, `benchmarks/results/r.json`, `benchmarks/results/summary.md`.

**Interfaces:** Produces `benchmarks/results/summary.md` with two Markdown tables — "Python packages" (rows: χ², G², Fisher-z, Pearson t, HSIC (n = 300), KCI (n = 300), KCI (n = 1 000), GCM, Pillai; columns: FastCIT, pgmpy dev, causal-learn, andrey-core; cells: median ms, "—" when not available) and "R packages" (rows: χ², G², Fisher-z, Pearson t, HSIC (median width); columns: FastCIT (R), pcalg, bnlearn, dHSIC) — plus a header block (date, CPU, OS, versions, commits) and an agreement table (largest |Δp| vs FastCIT per package/test).

- [ ] **Step 1:** `benchmarks/data.py` writes CSVs and `queries.json` into a given output dir (seeded; recipes in the spec). `python benchmarks/data.py OUTDIR` is idempotent.
- [ ] **Step 2:** `benchmarks/bench_python.py OUTDIR` and `benchmarks/bench_r.R OUTDIR` implement the timing method and write `python.json` / `r.json` (per engine/test: median ms, n queries, per-query p-values). Engines import normally (`import fastcit`, `import pgmpy`, …); the README says how to make them importable. Support `--quick` (2 queries per group) for a smoke run.
- [ ] **Step 3:** Smoke run with `--quick` for both scripts; fix errors.
- [ ] **Step 4:** Full run on a quiet machine (record `uptime` load before and after). Build/install FastCIT from this branch first: wheel into `<scratchpad>/site`, R package via `R CMD INSTALL` of a freshly built tarball into `cir-dev`. pgmpy dev from `git archive a67c17d9` into `<scratchpad>/pgmpy-dev-a67c17d9`.
- [ ] **Step 5:** `python benchmarks/summarize.py benchmarks/results` writes `summary.md`; commit scripts, `benchmarks/README.md` and the three result files.

### Task 2: Root README rewrite (ASD-STE100)

**Files:** Modify `README.md` only.

**Interfaces:** Consumes `benchmarks/results/summary.md` (copy the two main tables, with the machine/version line, and link to `benchmarks/`).

- [ ] **Step 1:** Rewrite per the spec's section list: title + tagline; one short paragraph; Install (four commands); Quick start with four collapsed `<details><summary>Python</summary>…</details>` blocks (Python, R, JavaScript, Rust), each one short example (build a dataset, run one test, print the p-value); Available tests (two columns: Test, Data type — twelve tests; GCM continuous, Pillai mixed); Performance (two tables + one sentence on method + link); Documentation/contributing links; License.
- [ ] **Step 2:** Verify every snippet by running it against the built packages (Python wheel in the scratchpad, `crates/ci-js/pkg` after `~/.cargo/bin/wasm-pack build --target nodejs --out-dir pkg`, the R package installed in `cir-dev`, Rust in a scratch crate depending on `crates/ci-core` by path). Record outputs in the report.
- [ ] **Step 3:** Check STE: list every sentence over the word limits (a small script is fine) and fix them; run `python -m pytest tests -q -p no:cacheprovider` (release tests read the README? confirm none break).
- [ ] **Step 4:** Commit.
