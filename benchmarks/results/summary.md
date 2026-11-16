# FastCIT benchmark summary

The first two tables give the median time of one test call, in milliseconds. The next two tables give the total time of one pass, in milliseconds. Lower is better.

Each language ran 3 times, each time in a new process. A cell gives the median of the run values. The spread tables give the smallest and largest run value of each cell. † marks a cell whose run values differ by more than 25 % of the cell value.

## Setup

- Python run: 3 runs, Intel(R) Core(TM) Ultra 5 125U (14 logical CPUs), Linux 6.8.0-147-generic, Python 3.14.2
  - versions: causal-learn 0.1.4.5, fastcit 0.1.0, gcastle 1.0.4, hyppo 0.5.2, pgmpy 1.1.0 (dev a67c17d9), pingouin 0.7.0, tigramite 5.2.10.1, numpy 2.4.1, pandas 3.0.0, scipy 1.17.0, scikit-learn 1.8.0
  - commits: fastcit 62f2425, pgmpy a67c17d9
  - FastCIT code (git tree hashes, check with `git rev-parse <commit>:<path>`): crates/ci-core 272b705c141858b431bc2e572b63cecf9940435d, crates/ci-python 2e8e9190b9a2392f5f9f918b838b75b131ca6761
  - helper packages: threadpoolctl 3.6.0, statsmodels 0.15.0, pandas-flavor 0.8.1, tabulate 0.10.0, xarray 2026.9.0, lazy_loader 0.6, autograd 1.9.1, numba 0.68.1, llvmlite 0.50.0, patsy 1.0.3, future 1.0.0
  - passes: 5 per run; each pass runs the engines of a row in a new random order (seeds 1, 2, 3)
  - CPU affinity: cpus_allowed_list 0-11; sched_getaffinity [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
  - threads: FastCIT single-threaded (no rayon); environment variables: none set
  - pools: openblas (libscipy_openblas-6cdc3b4a.so), 12 threads; openblas (libscipy_openblas64_-fdde5778.so), 12 threads; openmp (libgomp-e985bcbb.so.1.0.0), 12 threads
  - run 1 (python-1.json): 2026-11-16 23:01:25
    - power: AC online 1, profile performance, CPU 0 governor powersave, EPP performance
    - harness floor (median time of a no-op call, not subtracted): 0.00005 ms
    - uptime before: `23:01:25 up  9:22,  1 user,  load average: 1.45, 1.22, 1.00`
    - uptime after: `23:04:25 up  9:25,  1 user,  load average: 4.70, 3.59, 1.99`
  - run 2 (python-2.json): 2026-11-16 23:06:19
    - power: AC online 1, profile performance, CPU 0 governor powersave, EPP performance
    - harness floor (median time of a no-op call, not subtracted): 0.00005 ms
    - uptime before: `23:06:19 up  9:27,  1 user,  load average: 2.42, 2.87, 1.90`
    - uptime after: `23:09:06 up  9:30,  1 user,  load average: 4.27, 3.92, 2.48`
  - run 3 (python-3.json): 2026-11-16 23:11:31
    - power: AC online 1, profile performance, CPU 0 governor powersave, EPP performance
    - harness floor (median time of a no-op call, not subtracted): 0.00005 ms
    - uptime before: `23:11:31 up  9:32,  1 user,  load average: 1.34, 2.78, 2.25`
    - uptime after: `23:14:22 up  9:35,  1 user,  load average: 3.63, 3.66, 2.70`
- Python run (engines dowhy, fastcit; rows gcm): 3 runs, Intel(R) Core(TM) Ultra 5 125U (14 logical CPUs), Linux 6.8.0-147-generic, Python 3.11.10
  - versions: dowhy 0.14, fastcit 0.1.0, numpy 2.4.6, pandas 3.1.1, scipy 1.15.3, scikit-learn 1.9.1
  - commits: fastcit 62f2425
  - FastCIT code (git tree hashes, check with `git rev-parse <commit>:<path>`): crates/ci-core 272b705c141858b431bc2e572b63cecf9940435d, crates/ci-python 2e8e9190b9a2392f5f9f918b838b75b131ca6761
  - helper packages: threadpoolctl 3.8.0, statsmodels 0.15.0, numba 0.68.1, llvmlite 0.50.0, patsy 1.0.3
  - passes: 5 per run; each pass runs the engines of a row in a new random order (seeds 1, 2, 3)
  - CPU affinity: cpus_allowed_list 0-11; sched_getaffinity [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
  - threads: FastCIT single-threaded (no rayon); environment variables: none set
  - pools: openblas (libscipy_openblas-68440149.so), 12 threads; openblas (libscipy_openblas64_-32a4b2a6.so), 12 threads; openmp (libgomp-e985bcbb.so.1.0.0), 12 threads
  - same-interpreter reference (not a table column): GCM, FastCIT 0.404 ms per call (runs 0.401–0.405 ms)
  - run 1 (python-dowhy-1.json): 2026-11-16 23:05:47
    - power: AC online 1, profile performance, CPU 0 governor powersave, EPP performance
    - harness floor (median time of a no-op call, not subtracted): 0.00006 ms
    - uptime before: `23:05:47 up  9:27,  1 user,  load average: 1.49, 2.83, 1.85`
    - uptime after: `23:05:49 up  9:27,  1 user,  load average: 1.45, 2.80, 1.85`
  - run 2 (python-dowhy-2.json): 2026-11-16 23:10:58
    - power: AC online 1, profile performance, CPU 0 governor powersave, EPP performance
    - harness floor (median time of a no-op call, not subtracted): 0.00006 ms
    - uptime before: `23:10:58 up  9:32,  1 user,  load average: 1.36, 2.96, 2.29`
    - uptime after: `23:11:00 up  9:32,  1 user,  load average: 1.33, 2.93, 2.28`
  - run 3 (python-dowhy-3.json): 2026-11-16 23:15:24
    - power: AC online 1, profile performance, CPU 0 governor powersave, EPP performance
    - harness floor (median time of a no-op call, not subtracted): 0.00006 ms
    - uptime before: `23:15:24 up  9:36,  1 user,  load average: 1.34, 2.97, 2.52`
    - uptime after: `23:15:26 up  9:36,  1 user,  load average: 1.34, 2.97, 2.52`
- R run: 3 runs, Intel(R) Core(TM) Ultra 5 125U (14 logical CPUs), Linux 6.8.0-147-generic, R version 4.5.3 (2026-03-11)
  - versions: fastcit 0.0.0.9000, pcalg 2.7.12, bnlearn 5.2.1, dHSIC 2.2, Rfast 2.1.5.2, ppcor 1.1, comets 0.2.3
  - commits: fastcit 62f2425
  - FastCIT code (git tree hashes, check with `git rev-parse <commit>:<path>`): crates/ci-core 272b705c141858b431bc2e572b63cecf9940435d, crates/ci-r b57410fa1638ebb163983513b55d7924b048b5e7
  - passes: 5 per run; each pass runs the engines of a row in a new random order (seeds 1, 2, 3)
  - CPU affinity: cpus_allowed_list 0-3
  - threads: FastCIT single-threaded (no rayon); environment variables: none set
  - blas: libopenblasp-r0.3.34.so
  - lapack: libopenblasp-r0.3.34.so
  - run 1 (r-1.json): 2026-11-16 23:05:51
    - power: AC online 1, profile performance, CPU 0 governor powersave, EPP performance
    - harness floor (median time of a no-op call, not subtracted): 0.00429 ms
    - uptime before: `23:05:51 up  9:27,  1 user,  load average: 1.45, 2.80, 1.85`
    - uptime after: `23:06:18 up  9:27,  1 user,  load average: 1.41, 2.69, 1.84`
  - run 2 (r-2.json): 2026-11-16 23:11:03
    - power: AC online 1, profile performance, CPU 0 governor powersave, EPP performance
    - harness floor (median time of a no-op call, not subtracted): 0.00429 ms
    - uptime before: `23:11:03 up  9:32,  1 user,  load average: 1.33, 2.93, 2.28`
    - uptime after: `23:11:30 up  9:32,  1 user,  load average: 1.34, 2.78, 2.25`
  - run 3 (r-3.json): 2026-11-16 23:15:28
    - power: AC online 1, profile performance, CPU 0 governor powersave, EPP performance
    - harness floor (median time of a no-op call, not subtracted): 0.00429 ms
    - uptime before: `23:15:28 up  9:36,  1 user,  load average: 1.31, 2.94, 2.51`
    - uptime after: `23:15:55 up  9:37,  1 user,  load average: 1.44, 2.85, 2.49`

Quick run (2 queries per group): no

## Python packages, median time of one call

| Test | FastCIT | pgmpy dev | causal-learn | gcastle | tigramite | pingouin | hyppo | dowhy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| χ² | 0.049 | 0.098ᵇ | 0.128 | 8.47ᵇ | — | — | — | — |
| G² | 0.048 | 0.094ᵇ* | 0.131 | 8.46ᵇ | 1.78 | — | — | — |
| Cressie-Read | 0.050 | 0.098ᵇ | — | 8.63ᵇ | — | — | — | — |
| Freeman-Tukey | 0.050 | 0.094ᵇ* | — | 3.68ᵇ* | — | — | — | — |
| Modified log-likelihood | 0.048 | 0.091ᵇ* | — | 8.67ᵇ | — | — | — | — |
| Fisher-zᵈ | 0.001 | 0.945 | 0.043 | 0.143 | — | — | — | — |
| Pearson tᵈ | 0.001 | 0.880 | — | — | 1.65 | 3.59 | — | — |
| HSIC (n = 300) | 1.21 | 1.66 | 1.67ᶜ | — | — | — | 3.67ᶜ | — |
| KCI (n = 300) | 17.3 | 16.3 | 27.8ᶜ | — | — | — | — | — |
| KCI (n = 1 000) | 503 | 258 | 449 | — | — | — | — | — |
| GCM | 0.404 | 4.03 | — | — | — | — | — | 1.65 |
| Pillai | 0.143 | 141ᵃ | — | — | — | — | — | — |

ᵃ pgmpy runs a random-forest Pillai test. FastCIT runs a linear Pillai test. The two tests differ.
ᵇ pgmpy and gcastle apply the Yates correction on 2 × 2 tables and cannot turn it off. FastCIT runs without it.
ᶜ Different null approximation or kernel width rule from FastCIT.
ᵈ The time does not include the one-time setup. FastCIT and causal-learn precompute the correlation matrix. FastCIT computes it in the first call and keeps it. The other packages in these rows compute it in every call. See the total-time tables.
\* The engine raised an error or returned NaN on some queries. See the lists below. The median uses only the queries with a result. Those queries can cost less or more than the excluded ones. Compare such a cell with care.

## R packages, median time of one call

| Test | FastCIT (R) | pcalg | bnlearn | dHSIC | Rfast | ppcor | comets |
|---|---:|---:|---:|---:|---:|---:|---:|
| χ² | 0.067 | — | 0.302ᵉᶠ | — | 0.034ᵉ* | — | — |
| G² | 0.066 | 5.27ᵉ | 0.301ᵉᶠ | — | 0.041ᵉ | — | — |
| Fisher-zᵈ | 0.013 | 0.032 | 0.378ᶠ | — | — | — | — |
| Pearson tᵈ | 0.013 | — | 0.380ᶠ | — | — | 0.782ᵍ | — |
| HSIC (median width) | 1.41 | — | — | 5.79ᶜ | — | — | — |
| GCM | 0.479 | — | — | — | — | — | 20.8 |

ᶜ Different null approximation or kernel width rule from FastCIT.
ᵈ The time does not include the one-time setup. FastCIT and pcalg precompute the correlation matrix. FastCIT computes it in the first call and keeps it. bnlearn and ppcor compute it in every call. See the total-time tables.
ᵉ Uses the nominal degrees of freedom. FastCIT uses the adjusted degrees of freedom.
ᶠ bnlearn ci.test() checks the whole data frame in each call. The benchmark gives it only the columns of the query.
ᵍ ppcor needs at least one conditioning variable. For a query with an empty set, the benchmark calls stats::cor.test, which runs the same t-test.
\* The engine raised an error or returned NaN on some queries. See the lists below. The median uses only the queries with a result. Those queries can cost less or more than the excluded ones. Compare such a cell with care.

## Python packages, total time of one pass

Each pass builds the state of the engine (data conversion, test object, correlation matrix). Then it runs all queries of the group once. Each run keeps its fastest of 5 passes. The table shows the median of the 3 run values.

| Test | FastCIT | pgmpy dev | causal-learn | gcastle | tigramite | pingouin | hyppo | dowhy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| χ² | 5.87 | 16.4ᵇ | 10.3 | 583ᵇ | — | — | — | — |
| G² | 5.93 | 16.4ᵇ* | 10.5 | 581ᵇ | 97.6 | — | — | — |
| Cressie-Read | 5.89 | 16.8ᵇ | — | 581ᵇ | — | — | — | — |
| Freeman-Tukey | 5.81 | 16.4ᵇ* | — | 593ᵇ* | — | — | — | — |
| Modified log-likelihood | 5.74 | 16.2ᵇ* | — | 582ᵇ | — | — | — | — |
| Fisher-z | 3.72 | 46.4 | 4.46 | 8.35 | — | — | — | — |
| Pearson t | 3.69 | 43.3 | — | — | 83.4 | 183 | — | — |
| HSIC (n = 300) | 34.9 | 54.5 | 48.8ᶜ | — | — | — | 107ᶜ | — |
| KCI (n = 300) | 520 | 498 | 855ᶜ | — | — | — | — | — |
| KCI (n = 1 000) | 5 052 | 2 652 | 4 522 | — | — | — | — | — |
| GCM | 23.4 | 210 | — | — | — | — | — | 82.2 |
| Pillai | 6.63 | 9 784ᵃ | — | — | — | — | — | — |

ᵃ pgmpy runs a random-forest Pillai test. FastCIT runs a linear Pillai test. The two tests differ.
ᵇ pgmpy and gcastle apply the Yates correction on 2 × 2 tables and cannot turn it off. FastCIT runs without it.
ᶜ Different null approximation or kernel width rule from FastCIT.
\* The engine raised an error or returned NaN on some queries. The total includes the time of those queries.

## R packages, total time of one pass

Each run keeps its fastest of 5 passes. The table shows the median of the 3 run values. bnlearn, dHSIC, ppcor and comets have no setup.

| Test | FastCIT (R) | pcalg | bnlearn | dHSIC | Rfast | ppcor | comets |
|---|---:|---:|---:|---:|---:|---:|---:|
| χ² | 7.18 | — | 14.8ᵉᶠ | — | 2.63ᵉ* | — | — |
| G² | 7.05 | 447ᵉ | 15.1ᵉᶠ | — | 2.71ᵉ | — | — |
| Fisher-z | 4.33 | 6.31 | 19.3ᶠ | — | — | — | — |
| Pearson t | 4.41 | — | 19.3ᶠ | — | — | 38.8ᵍ | — |
| HSIC (median width) | 40.3 | — | — | 184ᶜ | — | — | — |
| GCM | 27.7 | — | — | — | — | — | 1 211 |

ᶜ Different null approximation or kernel width rule from FastCIT.
ᵉ Uses the nominal degrees of freedom. FastCIT uses the adjusted degrees of freedom.
ᶠ bnlearn ci.test() checks the whole data frame in each call. The benchmark gives it only the columns of the query.
ᵍ ppcor needs at least one conditioning variable. For a query with an empty set, the benchmark calls stats::cor.test, which runs the same t-test.
\* The engine raised an error or returned NaN on some queries. The total includes the time of those queries.

## Spread across runs

Each cell gives the smallest and the largest run value, in milliseconds.

### Python packages, median time of one call, range of the run values

| Test | FastCIT | pgmpy dev | causal-learn | gcastle | tigramite | pingouin | hyppo | dowhy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| χ² | 0.048–0.052 | 0.096–0.100 | 0.126–0.131 | 8.45–8.82 | — | — | — | — |
| G² | 0.048–0.049 | 0.094–0.097 | 0.128–0.132 | 8.37–8.57 | 1.77–1.79 | — | — | — |
| Cressie-Read | 0.050–0.051 | 0.098–0.100 | — | 8.58–8.64 | — | — | — | — |
| Freeman-Tukey | 0.049–0.050 | 0.092–0.098 | — | 3.64–3.73 | — | — | — | — |
| Modified log-likelihood | 0.048–0.048 | 0.090–0.094 | — | 8.57–8.79 | — | — | — | — |
| Fisher-z | 0.001–0.001 | 0.935–0.954 | 0.043–0.044 | 0.143–0.146 | — | — | — | — |
| Pearson t | 0.001–0.001 | 0.868–0.892 | — | — | 1.64–1.66 | 3.51–3.61 | — | — |
| HSIC (n = 300) | 1.21–1.21 | 1.59–1.67 | 1.66–1.69 | — | — | — | 3.62–3.69 | — |
| KCI (n = 300) | 17.1–17.9 | 16.1–17.1 | 25.8–28.3 | — | — | — | — | — |
| KCI (n = 1 000) | 455–505 | 243–265 | 418–459 | — | — | — | — | — |
| GCM | 0.400–0.405 | 3.94–4.08 | — | — | — | — | — | 1.63–1.65 |
| Pillai | 0.137–0.149 | 137–144 | — | — | — | — | — | — |

### Python packages, total time of one pass, range of the run values

| Test | FastCIT | pgmpy dev | causal-learn | gcastle | tigramite | pingouin | hyppo | dowhy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| χ² | 5.80–5.99 | 16.4–16.4 | 10.2–10.5 | 570–599 | — | — | — | — |
| G² | 5.73–5.95 | 16.3–16.5 | 10.4–10.7 | 566–595 | 96.9–98.6 | — | — | — |
| Cressie-Read | 5.74–6.02 | 16.5–17.0 | — | 579–594 | — | — | — | — |
| Freeman-Tukey | 5.73–5.91 | 16.2–16.6 | — | 587–594 | — | — | — | — |
| Modified log-likelihood | 5.72–5.93 | 16.1–16.3 | — | 573–594 | — | — | — | — |
| Fisher-z | 3.68–3.73 | 46.4–46.8 | 4.34–4.58 | 8.11–8.41 | — | — | — | — |
| Pearson t | 3.69–3.70 | 43.0–44.0 | — | — | 83.3–83.9 | 180–187 | — | — |
| HSIC (n = 300) | 34.9–35.1 | 52.5–56.9 | 48.5–49.3 | — | — | — | 105–108 | — |
| KCI (n = 300) | 515–541 | 484–531 | 782–882 | — | — | — | — | — |
| KCI (n = 1 000) | 4 576–5 053 | 2 453–2 672 | 4 243–4 681 | — | — | — | — | — |
| GCM | 23.4–23.9 | 209–216 | — | — | — | — | — | 81.3–82.9 |
| Pillai | 6.28–7.01 | 9 742–9 794 | — | — | — | — | — | — |

### R packages, median time of one call, range of the run values

| Test | FastCIT (R) | pcalg | bnlearn | dHSIC | Rfast | ppcor | comets |
|---|---:|---:|---:|---:|---:|---:|---:|
| χ² | 0.067–0.070 | — | 0.300–0.303 | — | 0.034–0.034 | — | — |
| G² | 0.065–0.067 | 5.05–5.36 | 0.301–0.302 | — | 0.040–0.041 | — | — |
| Fisher-z | 0.012–0.013 | 0.032–0.032 | 0.377–0.381 | — | — | — | — |
| Pearson t | 0.013–0.013 | — | 0.376–0.381 | — | — | 0.779–0.788 | — |
| HSIC (median width) | 1.39–1.42 | — | — | 5.78–5.84 | — | — | — |
| GCM | 0.473–0.482 | — | — | — | — | — | 20.7–20.8 |

### R packages, total time of one pass, range of the run values

| Test | FastCIT (R) | pcalg | bnlearn | dHSIC | Rfast | ppcor | comets |
|---|---:|---:|---:|---:|---:|---:|---:|
| χ² | 7.06–7.23 | — | 14.6–14.9 | — | 2.63–2.67 | — | — |
| G² | 6.98–7.18 | 442–447 | 14.8–15.1 | — | 2.71–2.85 | — | — |
| Fisher-z | 4.27–4.77 | 6.25–6.41 | 19.1–19.6 | — | — | — | — |
| Pearson t | 4.21–4.79 | — | 19.3–19.5 | — | — | 38.3–40.0 | — |
| HSIC (median width) | 40.2–40.7 | — | — | 183–184 | — | — | — |
| GCM | 27.3–27.9 | — | — | — | — | — | 1 205–1 215 |

No cell has run values that differ by more than 25 % of the cell value.

## Errors and NaN

Python:
- G², pgmpy: 0 errors, 1 NaN of 50 queries
- Freeman-Tukey, pgmpy: 0 errors, 15 NaN of 50 queries
- Freeman-Tukey, gcastle: 0 errors, 15 NaN of 50 queries
- Modified log-likelihood, pgmpy: 0 errors, 1 NaN of 50 queries
R:
- chi-squared, Rfast: 0 errors, 6 NaN of 50 queries

## Agreement, Python packages

| Test | Package | Largest abs. difference in p-value | Queries compared | Errors | NaN | Note |
|---|---|---:|---:|---:|---:|---|
| χ² | pgmpy | 8.90e-14 | 50 | 0 | 0 | compared with FastCIT with Yates on (pgmpy cannot turn it off) |
| χ² | causal-learn | 9.51e-14 | 50 | 0 | 0 |  |
| χ² | gcastle | 8.85e-14 | 50 | 0 | 0 | compared with FastCIT with Yates on (gcastle cannot turn it off) |
| G² | pgmpy | 1.92e-12 | 49 | 0 | 1 | compared with FastCIT with Yates on (pgmpy cannot turn it off) |
| G² | causal-learn | 1.03e-13 | 50 | 0 | 0 |  |
| G² | gcastle | 1.04e-13 | 50 | 0 | 0 | compared with FastCIT with Yates on (gcastle cannot turn it off) |
| G² | tigramite | 1.63e-12 | 50 | 0 | 0 |  |
| Cressie-Read | pgmpy | 6.23e-12 | 50 | 0 | 0 | compared with FastCIT with Yates on (pgmpy cannot turn it off) |
| Cressie-Read | gcastle | 6.23e-12 | 50 | 0 | 0 | compared with FastCIT with Yates on (gcastle cannot turn it off) |
| Freeman-Tukey | pgmpy | 4.67e-13 | 35 | 0 | 15 | compared with FastCIT with Yates on (pgmpy cannot turn it off) |
| Freeman-Tukey | gcastle | 4.69e-13 | 35 | 0 | 15 | compared with FastCIT with Yates on (gcastle cannot turn it off) |
| Modified log-likelihood | pgmpy | 2.00e-12 | 49 | 0 | 1 | compared with FastCIT with Yates on (pgmpy cannot turn it off) |
| Modified log-likelihood | gcastle | 5.31e-14 | 50 | 0 | 0 | compared with FastCIT with Yates on (gcastle cannot turn it off) |
| Fisher-z | pgmpy | 4.69e-11 | 50 | 0 | 0 |  |
| Fisher-z | causal-learn | 4.69e-11 | 50 | 0 | 0 |  |
| Fisher-z | gcastle | 4.69e-11 | 50 | 0 | 0 |  |
| Pearson t | pgmpy | 5.69e-11 | 50 | 0 | 0 |  |
| Pearson t | tigramite | 5.69e-11 | 50 | 0 | 0 |  |
| Pearson t | pingouin | 5.69e-11 | 50 | 0 | 0 |  |
| HSIC (n = 300) | pgmpy | 2.82e-14 | 28 | 0 | 0 |  |
| HSIC (n = 300) | causal-learn | 3.96e-01 | 28 | 0 | 0 | unconditional kci; kernel width or null approximation differs |
| HSIC (n = 300) | hyppo | 4.26e-01 | 28 | 0 | 0 | chi-squared null approximation, not gamma |
| KCI (n = 300) | pgmpy | 3.37e-12 | 30 | 0 | 0 |  |
| KCI (n = 300) | causal-learn | 7.40e-04 | 30 | 0 | 0 | kernel width or null approximation differs |
| KCI (n = 1 000) | pgmpy | 9.50e-12 | 10 | 0 | 0 |  |
| KCI (n = 1 000) | causal-learn | 2.67e-12 | 10 | 0 | 0 |  |
| GCM | pgmpy | 4.78e-11 | 50 | 0 | 0 |  |
| GCM | dowhy | 4.78e-11 | 50 | 0 | 0 |  |
| Pillai | pgmpy | 2.24e-01 | 40 | 0 | 0 | random forest, different test |

## Agreement, R packages

| Test | Package | Largest abs. difference in p-value | Queries compared | Errors | NaN | Note |
|---|---|---:|---:|---:|---:|---|
| χ² | bnlearn | 4.29e-01 | 50 | 0 | 0 | default x2 uses nominal dof (see the adf row) |
| χ² | bnlearn (adf) | 9.50e-14 | 50 | 0 | 0 |  |
| χ² | Rfast | 2.81e-01 | 44 | 0 | 6 | nominal dof, like bnlearn; NaN when a table has an empty row or column |
| G² | pcalg | 4.29e-01 | 50 | 0 | 0 | nominal dof (adaptDF = FALSE) |
| G² | bnlearn | 4.29e-01 | 50 | 0 | 0 | default mi uses nominal dof (see the adf row) |
| G² | bnlearn (adf) | 3.87e-13 | 50 | 0 | 0 |  |
| G² | pcalg (adaptDF) | 9.71e-01 | 50 | 0 | 0 | pcalg adjusts dof by its own rule |
| G² | Rfast | 4.29e-01 | 50 | 0 | 0 | nominal dof, like bnlearn |
| Fisher-z | pcalg | 4.69e-11 | 50 | 0 | 0 |  |
| Fisher-z | bnlearn | 4.69e-11 | 50 | 0 | 0 |  |
| Pearson t | bnlearn | 5.69e-11 | 50 | 0 | 0 |  |
| Pearson t | ppcor | 5.69e-11 | 50 | 0 | 0 | queries with an empty Z use stats::cor.test |
| HSIC (median width) | dHSIC | 9.81e-03 | 28 | 0 | 0 | different kernel width or null approximation |
| GCM | comets | 4.78e-11 | 50 | 0 | 0 |  |

The agreement tables compare p-values on the same queries. A query with an error or NaN is not compared. The p-values come from the first run of each language. The R rows `bnlearn (adf)` and `pcalg (adaptDF)` use the adjusted degrees of freedom. They exist only for this comparison.
