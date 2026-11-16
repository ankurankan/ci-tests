# FastCIT benchmark summary

The first two tables give the median time of one test call, in milliseconds. The last two tables give the total time of one pass, in milliseconds. Lower is better.

## Setup

- Python run: 2026-11-16 19:19:50, Intel(R) Core(TM) Ultra 5 125U (14 logical CPUs), Linux 6.8.0-147-generic
  - versions: fastcit 0.1.0, pgmpy 1.1.0 (dev a67c17d9), causal-learn 0.1.4.5, andrey-core 0.17.1, numpy 2.4.1, pandas 3.0.0, scipy 1.17.0, scikit-learn 1.8.0
  - commits: fastcit b4dafa4, pgmpy a67c17d9
  - passes: 3
  - CPU affinity: not recorded
  - threads: FastCIT single-threaded (no rayon); environment variables: none set
  - pools: openblas (libscipy_openblas64_-fdde5778.so), 14 threads; openblas (libscipy_openblas-6cdc3b4a.so), 14 threads; openmp (libgomp-e985bcbb.so.1.0.0), 14 threads
  - uptime before: `19:19:50 up  5:41,  1 user,  load average: 1.50, 3.31, 3.87`
  - uptime after: `19:22:12 up  5:43,  1 user,  load average: 8.46, 6.25, 4.93`
- R run: 2026-11-16 19:46:06, Intel(R) Core(TM) Ultra 5 125U (14 logical CPUs), Linux 6.8.0-147-generic
  - versions: fastcit 0.0.0.9000, pcalg 2.7.12, bnlearn 5.2.1, dHSIC 2.2
  - commits: fastcit 6361fa3
  - passes: 3
  - CPU affinity: cpus_allowed_list 0-3
  - threads: FastCIT single-threaded (no rayon); environment variables: none set
  - blas: /home/ankur/miniconda3/envs/cir-dev/lib/libopenblasp-r0.3.34.so
  - lapack: /home/ankur/miniconda3/envs/cir-dev/lib/libopenblasp-r0.3.34.so
  - uptime before: `19:46:06 up  6:07,  1 user,  load average: 1.18, 2.10, 3.15`
  - uptime after: `19:46:14 up  6:07,  1 user,  load average: 1.30, 2.10, 3.14`

Quick run (2 queries per group): no

## Python packages, median time of one call

| Test | FastCIT | pgmpy dev | causal-learn | andrey-core |
|---|---:|---:|---:|---:|
| χ² | 0.124 | 0.238ᶜ | 0.328 | 0.283ᵇ |
| G² | 0.118 | 0.162ᶜ* | 0.173 | 0.259ᵇ |
| Fisher-zᵉ | 0.001 | 1.01 | 0.044 | 0.013 |
| Pearson tᵉ | 0.001 | 0.965 | — | 0.013 |
| HSIC (n = 300) | 0.902 | 1.68 | 1.81ᵈ | 1.49ᵈ |
| KCI (n = 300) | 18.2 | 37.8 | 54.2 | 13.0 |
| KCI (n = 1 000) | 482 | 383 | 900 | 392 |
| GCM | 0.592 | 4.02 | — | — |
| Pillai | 0.124 | 142ᵃ | — | — |

ᵃ pgmpy runs a random-forest Pillai test. FastCIT runs a linear Pillai test. The two tests differ.
ᵇ andrey-core χ² and G² use a different degrees-of-freedom rule from FastCIT.
ᶜ pgmpy applies the Yates correction and cannot turn it off. FastCIT runs without it.
ᵈ Different null approximation or kernel width rule from FastCIT.
ᵉ The time does not include the one-time setup. FastCIT, causal-learn and andrey-core precompute the correlation matrix. FastCIT computes it in the first call and keeps it. pgmpy computes it in every call. With the setup included, andrey-core finishes a pass faster than FastCIT on Fisher-z and Pearson t. See the total-time tables.
\* The engine raised an error or returned NaN on some queries. The median leaves them out. See the lists below.

## R packages, median time of one call

| Test | FastCIT (R) | pcalg | bnlearn | dHSIC |
|---|---:|---:|---:|---:|
| χ² | 0.212 | — | 0.635ᶠᵍ | — |
| G² | 0.093 | 11.6ᶠ | 0.315ᶠᵍ | — |
| Fisher-zᵉ | 0.015 | 0.033 | 0.398ᵍ | — |
| Pearson tᵉ | 0.013 | — | 0.394ᵍ | — |
| HSIC (median width) | 1.40 | — | — | 6.10ᵈ |

ᵈ Different null approximation or kernel width rule from FastCIT.
ᵉ The time does not include the one-time setup. FastCIT and pcalg precompute the correlation matrix. FastCIT computes it in the first call and keeps it. bnlearn computes it in every call. See the total-time tables.
ᶠ Uses the nominal degrees of freedom. FastCIT uses the adjusted degrees of freedom.
ᵍ bnlearn ci.test() checks the whole data frame in each call. The benchmark gives it only the columns of the query.

## Python packages, total time of one pass

Each pass builds the state of the engine (data conversion, test object, correlation matrix) and then runs all queries of the group once. The table shows the best of 3 passes.

| Test | FastCIT | pgmpy dev | causal-learn | andrey-core |
|---|---:|---:|---:|---:|
| χ² | 13.9 | 39.5 | 24.6 | 24.0 |
| G² | 14.0 | 26.9* | 13.6 | 20.3 |
| Fisher-z | 3.70 | 49.7 | 4.59 | 1.89 |
| Pearson t | 3.61 | 46.1 | — | 1.80 |
| HSIC (n = 300) | 26.0 | 54.9 | 51.9 | 44.0 |
| KCI (n = 300) | 546 | 1 441 | 1 758 | 336 |
| KCI (n = 1 000) | 4 806 | 3 910 | 10 814 | 4 290 |
| GCM | 34.7 | 221 | — | — |
| Pillai | 5.88 | 10 299 | — | — |

\* The engine raised an error or returned NaN on some queries. The total includes the time of those queries.

## R packages, total time of one pass

The table shows the best of 3 passes. bnlearn and dHSIC have no setup.

| Test | FastCIT (R) | pcalg | bnlearn | dHSIC |
|---|---:|---:|---:|---:|
| χ² | 25.2 | — | 31.5 | — |
| G² | 9.96 | 1 333 | 15.4 | — |
| Fisher-z | 4.54 | 6.21 | 19.8 | — |
| Pearson t | 4.50 | — | 19.9 | — |
| HSIC (median width) | 39.5 | — | — | 192 |

## Errors and NaN

Python:
- G², pgmpy: 0 errors, 1 NaN of 50 queries

## Agreement, Python packages

| Test | Package | Largest abs. difference in p-value | Queries compared | Errors | NaN | Note |
|---|---|---:|---:|---:|---:|---|
| χ² | pgmpy | 8.90e-14 | 50 | 0 | 0 | compared with FastCIT with Yates on (pgmpy cannot turn it off) |
| χ² | causal-learn | 9.51e-14 | 50 | 0 | 0 |  |
| χ² | andrey-core | 6.93e-02 | 50 | 0 | 0 | different dof rule |
| G² | pgmpy | 1.92e-12 | 49 | 0 | 1 | compared with FastCIT with Yates on (pgmpy cannot turn it off) |
| G² | causal-learn | 1.03e-13 | 50 | 0 | 0 |  |
| G² | andrey-core | 1.85e-01 | 50 | 0 | 0 | different dof rule |
| Fisher-z | pgmpy | 4.69e-11 | 50 | 0 | 0 |  |
| Fisher-z | causal-learn | 4.69e-11 | 50 | 0 | 0 |  |
| Fisher-z | andrey-core | 4.69e-11 | 50 | 0 | 0 |  |
| Pearson t | pgmpy | 5.69e-11 | 50 | 0 | 0 |  |
| Pearson t | andrey-core | 5.69e-11 | 50 | 0 | 0 |  |
| HSIC (n = 300) | pgmpy | 3.95e-14 | 28 | 0 | 0 |  |
| HSIC (n = 300) | causal-learn | 9.53e-03 | 28 | 0 | 0 | unconditional kci; kernel width or null approximation differs |
| HSIC (n = 300) | andrey-core | 9.53e-03 | 28 | 0 | 0 | unconditional kci; kernel width or null approximation differs |
| KCI (n = 300) | pgmpy | 4.34e-12 | 30 | 0 | 0 |  |
| KCI (n = 300) | causal-learn | 7.40e-04 | 30 | 0 | 0 | kernel width or null approximation differs |
| KCI (n = 300) | andrey-core | 5.12e-03 | 30 | 0 | 0 | andrey-core uses the other x/y orientation; compared with FastCIT swapped |
| KCI (n = 1 000) | pgmpy | 7.48e-12 | 10 | 0 | 0 |  |
| KCI (n = 1 000) | causal-learn | 1.87e-12 | 10 | 0 | 0 |  |
| KCI (n = 1 000) | andrey-core | 3.46e-03 | 10 | 0 | 0 | andrey-core uses the other x/y orientation; compared with FastCIT swapped |
| GCM | pgmpy | 4.78e-11 | 50 | 0 | 0 |  |
| Pillai | pgmpy | 2.24e-01 | 40 | 0 | 0 | random forest, different test |

## Agreement, R packages

| Test | Package | Largest abs. difference in p-value | Queries compared | Errors | NaN | Note |
|---|---|---:|---:|---:|---:|---|
| χ² | bnlearn | 4.29e-01 | 50 | 0 | 0 | default x2 uses nominal dof (see the adf row) |
| χ² | bnlearn (adf) | 9.50e-14 | 50 | 0 | 0 |  |
| G² | pcalg | 4.29e-01 | 50 | 0 | 0 | nominal dof (adaptDF = FALSE) |
| G² | bnlearn | 4.29e-01 | 50 | 0 | 0 | default mi uses nominal dof (see the adf row) |
| G² | bnlearn (adf) | 3.87e-13 | 50 | 0 | 0 |  |
| G² | pcalg (adaptDF) | 9.71e-01 | 50 | 0 | 0 | pcalg adjusts dof by its own rule |
| Fisher-z | pcalg | 4.69e-11 | 50 | 0 | 0 |  |
| Fisher-z | bnlearn | 4.69e-11 | 50 | 0 | 0 |  |
| Pearson t | bnlearn | 5.69e-11 | 50 | 0 | 0 |  |
| HSIC (median width) | dHSIC | 9.81e-03 | 28 | 0 | 0 | different kernel width or null approximation |

The agreement tables compare p-values on the same queries. A query with an error or NaN is not compared. The R rows `bnlearn (adf)` and `pcalg (adaptDF)` use the adjusted degrees of freedom. They exist only for this comparison.
