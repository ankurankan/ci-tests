# FastCIT sweep benchmark

The tables give the median time of one test call, in milliseconds. Lower is better. Each test has one table for the sample size n and one for the conditioning-set size |Z|. Each column is one value of n or |Z|.

Each cell is the median over the queries of a point. Each query keeps its fastest pass. An engine that passes the time budget skips the larger points. HSIC and KCI do not run above their memory limit. — means no result. Other marks are explained under each table.

## Setup

- Python: Python 3.14.2, AMD Ryzen 9 7950X 16-Core Processor (32 logical CPUs), Linux 7.0.0-42-generic, 2026-11-18 09:01:04; passes per point: 3; time budget: 60 s.
  - versions: causal-learn 0.1.4.5, fastcit 0.1.0, gcastle 1.0.4, hyppo 0.5.2, pgmpy 1.1.2, pingouin 0.7.0, tigramite 5.2.10.1, numpy 2.4.1, pandas 3.0.0, scipy 1.17.0, scikit-learn 1.8.0
  - dowhy run: Python 3.11.10, 2026-11-18 10:05:23, versions: dowhy 0.14, fastcit 0.1.0, numpy 2.4.6, pandas 3.1.1, scipy 1.15.3, scikit-learn 1.9.1
  - same-interpreter FastCIT reference (gcm, n, not a table row): 0.0033, 0.0090, 0.028, 0.081, 0.268, 0.804, 2.69 ms
  - same-interpreter FastCIT reference (gcm, z, not a table row): 0.017, 0.028, 0.039, 0.052, 0.066, 0.095, 0.133 ms
- R: R version 4.5.3 (2026-03-11), AMD Ryzen 9 7950X 16-Core Processor (32 logical CPUs), Linux 7.0.0-42-generic, 2026-11-18 10:05:30; passes per point: 3; time budget: 60 s.
  - versions: fastcit 0.0.0.9000, pcalg 2.7.12, bnlearn 5.2.1, dHSIC 2.2, Rfast 2.1.5.2, ppcor 1.1, comets 0.2.3

### Python, χ², sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.0020 | 0.0027 | 0.0053 | 0.013 | 0.040 | 0.111 | 0.376 |
| pgmpy devᵃ | 0.048 | 0.050 | 0.050 | 0.054 | 0.069 | 0.103 | 0.237 |
| causal-learn | 0.062 | 0.063 | 0.063 | 0.070 | 0.095 | 0.159 | 0.387 |
| gcastleᵃ | 1.87 | 1.90 | 1.94 | 2.02 | 3.73 | 5.02 | 12.3 |

- ᵃ pgmpy and gcastle apply the Yates correction on 2 × 2 tables and cannot turn it off. FastCIT runs without it.

### Python, χ², conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.0015 | 0.0055 | 0.0068 | 0.0095 | 0.016 | 0.029 | 0.032 |
| pgmpy devᵃ | 0.048 | 0.053 | 0.054 | 0.059 | 0.078 | 0.210 | 0.843 |
| causal-learn | 0.051 | 0.066 | 0.069 | 0.075 | 0.088 | 0.164 | 0.288 |
| gcastleᵃ | 0.598 | 1.92 | 5.41 | 13.0 | 34.4 | 151 | 283 |

- ᵃ pgmpy and gcastle apply the Yates correction on 2 × 2 tables and cannot turn it off. FastCIT runs without it.

### Python, G², sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.0019 | 0.0026 | 0.0055 | 0.013 | 0.039 | 0.114 | 0.370 |
| pgmpy devᵃ | 0.046 | 0.047 | 0.049 | 0.053 | 0.066 | 0.102 | 0.239 |
| causal-learn | 0.064 | 0.063 | 0.066 | 0.072 | 0.097 | 0.161 | 0.392 |
| gcastleᵃ | 1.86 | 1.88 | 1.92 | 2.03 | 2.33 | 3.29 | 12.8 |
| tigramite | 0.238 | 0.277 | 0.360 | 0.672 | 1.61 | 3.70 | 13.4 |

- ᵃ pgmpy and gcastle apply the Yates correction on 2 × 2 tables and cannot turn it off. FastCIT runs without it.

### Python, G², conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.0013 | 0.0053 | 0.0061 | 0.0077 | 0.011 | 0.023 | 0.029 |
| pgmpy devᵃ | 0.045 | 0.048 | 0.052* | 0.058* | —§ | —§ | —§ |
| causal-learn | 0.050 | 0.066 | 0.071 | 0.074 | 0.090 | 0.176 | 0.300 |
| gcastleᵃ | 0.594 | 1.91 | 5.25 | 12.9 | 34.4 | 150 | 280 |
| tigramite | 0.280 | 0.358 | 0.567 | 0.885 | 1.84 | 10.6 | 45.9 |

- ᵃ pgmpy and gcastle apply the Yates correction on 2 × 2 tables and cannot turn it off. FastCIT runs without it.
- § No result. Every query raised an error or returned NaN, or fewer than half of them gave a value. pgmpy dev at 4: 17 of 20 queries gave NaN or an error.
- \* Some queries raised an error or returned NaN. The median uses the other queries. pgmpy dev at 2: 2 of 20 queries left out; pgmpy dev at 3: 4 of 20 queries left out.

### Python, Cressie-Read, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.0021 | 0.0032 | 0.0057 | 0.013 | 0.042 | 0.120 | 0.383 |
| pgmpy devᵃ | 0.049 | 0.052 | 0.052 | 0.058 | 0.072 | 0.109 | 0.245 |
| gcastleᵃ | 1.90 | 1.97 | 2.04 | 2.18 | 2.44 | 3.45 | 11.9 |

- ᵃ pgmpy and gcastle apply the Yates correction on 2 × 2 tables and cannot turn it off. FastCIT runs without it.

### Python, Cressie-Read, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.0015 | 0.0055 | 0.0071 | 0.0095 | 0.017 | 0.029 | 0.032 |
| pgmpy devᵃ | 0.048 | 0.052 | 0.057 | 0.062 | 0.085 | 0.255 | 1.19 |
| gcastleᵃ | 0.620 | 2.00 | 5.42 | 13.6 | 35.5 | 153 | 280 |

- ᵃ pgmpy and gcastle apply the Yates correction on 2 × 2 tables and cannot turn it off. FastCIT runs without it.

### Python, Freeman-Tukey, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.0022 | 0.0031 | 0.0057 | 0.014 | 0.040 | 0.112 | 0.368 |
| pgmpy devᵃ | —§ | 0.052* | 0.052* | 0.055* | 0.073* | 0.104* | 0.239 |
| gcastleᵃ | —§ | 1.94* | 1.99* | 2.01* | 2.33* | 3.24* | 11.4 |

- ᵃ pgmpy and gcastle apply the Yates correction on 2 × 2 tables and cannot turn it off. FastCIT runs without it.
- § No result. Every query raised an error or returned NaN, or fewer than half of them gave a value. pgmpy dev at 100: 12 of 20 queries gave NaN or an error; gcastle at 100: 12 of 20 queries gave NaN or an error.
- \* Some queries raised an error or returned NaN. The median uses the other queries. pgmpy dev at 300: 9 of 20 queries left out; pgmpy dev at 1 000: 4 of 20 queries left out; pgmpy dev at 3 000: 3 of 20 queries left out; pgmpy dev at 10 000: 2 of 20 queries left out; pgmpy dev at 30 000: 1 of 20 queries left out; gcastle at 300: 9 of 20 queries left out; gcastle at 1 000: 4 of 20 queries left out; gcastle at 3 000: 3 of 20 queries left out; gcastle at 10 000: 2 of 20 queries left out; gcastle at 30 000: 1 of 20 queries left out.

### Python, Freeman-Tukey, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.0015 | 0.0056 | 0.0068 | 0.0089 | 0.016 | 0.028 | 0.032 |
| pgmpy devᵃ | 0.047 | 0.051* | —§ | —§ | —§ | —§ | —§ |
| gcastleᵃ | 0.594 | 1.91* | —§ | —§ | —§ | —§ | —§ |

- ᵃ pgmpy and gcastle apply the Yates correction on 2 × 2 tables and cannot turn it off. FastCIT runs without it.
- § No result. Every query raised an error or returned NaN, or fewer than half of them gave a value. pgmpy dev at 2: 15 of 20 queries gave NaN or an error; pgmpy dev at 3: 18 of 20 queries gave NaN or an error; pgmpy dev at 4: 19 of 20 queries gave NaN or an error; pgmpy dev at 6: 19 of 20 queries gave NaN or an error; pgmpy dev at 8: 17 of 20 queries gave NaN or an error; gcastle at 2: 15 of 20 queries gave NaN or an error; gcastle at 3: 18 of 20 queries gave NaN or an error; gcastle at 4: 19 of 20 queries gave NaN or an error; gcastle at 6: 19 of 20 queries gave NaN or an error; gcastle at 8: 17 of 20 queries gave NaN or an error.
- \* Some queries raised an error or returned NaN. The median uses the other queries. pgmpy dev at 1: 4 of 20 queries left out; gcastle at 1: 4 of 20 queries left out.

### Python, Modified log-likelihood, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.0019 | 0.0026 | 0.0054 | 0.013 | 0.040 | 0.115 | 0.370 |
| pgmpy devᵃ | 0.043 | 0.045 | 0.048 | 0.053 | 0.066 | 0.101 | 0.237 |
| gcastleᵃ | 1.87 | 1.88 | 1.92 | 2.02 | 2.32 | 3.26 | 11.6 |

- ᵃ pgmpy and gcastle apply the Yates correction on 2 × 2 tables and cannot turn it off. FastCIT runs without it.

### Python, Modified log-likelihood, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.0014 | 0.0053 | 0.0061 | 0.0075 | 0.012 | 0.023 | 0.028 |
| pgmpy devᵃ | 0.045 | 0.047 | 0.043* | 0.047* | —§ | —§ | —§ |
| gcastleᵃ | 0.596 | 1.91 | 5.24 | 13.0 | 34.5 | 149 | 278 |

- ᵃ pgmpy and gcastle apply the Yates correction on 2 × 2 tables and cannot turn it off. FastCIT runs without it.
- § No result. Every query raised an error or returned NaN, or fewer than half of them gave a value. pgmpy dev at 4: 17 of 20 queries gave NaN or an error.
- \* Some queries raised an error or returned NaN. The median uses the other queries. pgmpy dev at 2: 2 of 20 queries left out; pgmpy dev at 3: 4 of 20 queries left out.

### Python, Fisher-z, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCITᵃ | 0.00050 | 0.00051 | 0.00053 | 0.00051 | 0.00054 | 0.00054 | 0.00065 |
| pgmpy devᵃ | 0.380 | 0.383 | 0.403 | 0.458 | 0.636 | 1.11 | 2.72 |
| causal-learnᵃ | 0.030 | 0.030 | 0.030 | 0.029 | 0.030 | 0.029 | 0.029 |
| gcastleᵃ | 0.047 | 0.049 | 0.055 | 0.069 | 0.107 | 0.208 | 0.565 |

- ᵃ The time does not include the one-time setup. FastCIT builds the correlation matrix in its first call, and the median leaves that call out, so its time stays flat as n grows. causal-learn builds it at setup and stays flat too. pgmpy and pingouin build it in every call, so their time grows with n.

### Python, Fisher-z, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCITᵃ | 0.00047 | 0.00049 | 0.00057 | 0.00062 | 0.00069 | 0.00098 | 0.0012 |
| pgmpy devᵃ | 0.202 | 0.408 | 0.421 | 0.440 | 0.448 | 0.474 | 0.503 |
| causal-learnᵃ | 0.029 | 0.030 | 0.029 | 0.031 | 0.032 | 0.031 | 0.034 |
| gcastleᵃ | 0.044 | 0.054 | 0.052 | 0.058 | 0.059 | 0.061 | 0.066 |

- ᵃ The time does not include the one-time setup. FastCIT builds the correlation matrix in its first call, and the median leaves that call out, so its time stays flat as n grows. causal-learn builds it at setup and stays flat too. pgmpy and pingouin build it in every call, so their time grows with n.

### Python, Pearson t, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCITᵃ | 0.00066 | 0.00064 | 0.00072 | 0.00061 | 0.00066 | 0.00070 | 0.00077 |
| pgmpy devᵃ | 0.345 | 0.354 | 0.370 | 0.421 | 0.596 | 1.08 | 2.71 |
| tigramiteᵃ | 0.294 | 0.315 | 0.375 | 0.544 | 1.13 | 3.08 | 9.74 |
| pingouinᵃ | 1.37 | 1.39 | 1.43 | 1.61 | 1.97 | 2.95 | 7.92 |

- ᵃ The time does not include the one-time setup. FastCIT builds the correlation matrix in its first call, and the median leaves that call out, so its time stays flat as n grows. causal-learn builds it at setup and stays flat too. pgmpy and pingouin build it in every call, so their time grows with n.

### Python, Pearson t, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCITᵃ | 0.00055 | 0.00068 | 0.00072 | 0.00073 | 0.00078 | 0.0012 | 0.0015 |
| pgmpy devᵃ | 0.164 | 0.392 | 0.381 | 0.406 | 0.421 | 0.437 | 0.459 |
| tigramiteᵃ | 0.313 | 0.393 | 0.403 | 0.429 | 0.455 | 0.512 | 0.561 |
| pingouinᵃ | 1.35 | 1.47 | 1.51 | 1.61 | 1.69 | 1.84 | 2.02 |

- ᵃ The time does not include the one-time setup. FastCIT builds the correlation matrix in its first call, and the median leaves that call out, so its time stays flat as n grows. causal-learn builds it at setup and stays flat too. pgmpy and pingouin build it in every call, so their time grows with n.

### Python, Pearson equivalence, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCITᵃ | 0.00056 | 0.00054 | 0.00052 | 0.00057 | 0.00058 | 0.00058 | 0.00070 |
| pgmpy devᵃ | 0.406 | 0.413 | 0.435 | 0.491 | 0.666 | 1.15 | 2.73 |

- ᵃ The time does not include the one-time setup. FastCIT builds the correlation matrix in its first call, and the median leaves that call out, so its time stays flat as n grows. causal-learn builds it at setup and stays flat too. pgmpy and pingouin build it in every call, so their time grows with n.

### Python, Pearson equivalence, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCITᵃ | 0.00047 | 0.00054 | 0.00056 | 0.00067 | 0.00071 | 0.00097 | 0.0010 |
| pgmpy devᵃ | 0.231 | 0.439 | 0.451 | 0.464 | 0.478 | 0.501 | 0.531 |

- ᵃ The time does not include the one-time setup. FastCIT builds the correlation matrix in its first call, and the median leaves that call out, so its time stays flat as n grows. causal-learn builds it at setup and stays flat too. pgmpy and pingouin build it in every call, so their time grows with n.

### Python, HSIC, sample size (Z empty)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.125 | 1.09 | 12.2 | 183 | 2 097 | —¶ | —¶ |
| pgmpy dev | 0.365 | 0.830 | 7.07 | 106 | 953 | —¶ | —¶ |
| causal-learnᵃ | 0.322 | 0.802 | 7.37 | 138 | 1 355 | —¶ | —¶ |
| hyppoᵃ | 0.606 | 2.56 | 41.0 | 540 | 6 184† | —‡ | —‡ |

- ᵃ Different null approximation or kernel width rule from FastCIT.
- † The first pass took more than 60 s. The cell comes from one pass. Larger points, if any, are missing.
- ‡ No result. The engine skipped this point after it passed the time budget.
- ¶ No result. The sweep does not run this test at this sample size. The packages need too much memory there.

### Python, KCI, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 1.14 | 11.8 | 319 | 8 652† | —‡ | —‡ | —‡ |
| pgmpy dev | 1.67 | 7.67 | 106 | 1 498 | 76 801† | —‡ | —‡ |
| causal-learnᵃ | 2.09 | 12.5 | 173 | 3 141 | 190 326† | —‡ | —‡ |

- ᵃ Different null approximation or kernel width rule from FastCIT.
- † The first pass took more than 60 s. The cell comes from one pass. Larger points, if any, are missing.
- ‡ No result. The engine skipped this point after it passed the time budget.

### Python, KCI, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 9.27 | 316 | 336 | 347 | 349 | 357 | 364 |
| pgmpy dev | 6.95 | 108 | 110 | 115 | 119 | 120 | 121 |
| causal-learnᵃ | 7.28 | 177 | 183 | 198 | 215 | 218 | 219 |

- ᵃ Different null approximation or kernel width rule from FastCIT.

### Python, GCM, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.0033 | 0.0091 | 0.028 | 0.080 | 0.266 | 0.803 | 2.70 |
| pgmpy dev | 2.14 | 2.16 | 2.18 | 2.25 | 2.45 | 3.21 | 5.29 |
| dowhy | 0.582 | 0.594 | 0.620 | 0.698 | 0.946 | 1.65 | 4.06 |

### Python, GCM, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.018 | 0.028 | 0.039 | 0.052 | 0.065 | 0.095 | 0.131 |
| pgmpy dev | 2.14 | 2.18 | 2.20 | 2.23 | 2.26 | 2.30 | 2.35 |
| dowhy | 0.056 | 0.622 | 0.694 | 0.739 | 0.783 | 0.864 | 0.954 |

### Python, Pillai, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.0066 | 0.017 | 0.051 | 0.154 | 0.488 | 1.44 | 4.86 |
| pgmpy devᵃ | 77.1 | 88.8 | 158 | 417 | 1 648 | 6 171† | —‡ |

- ᵃ random forest (pgmpy default); a different test from FastCIT (linear)
- † The first pass took more than 60 s. The cell comes from one pass. Larger points, if any, are missing.
- ‡ No result. The engine skipped this point after it passed the time budget.

### Python, Pillai, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.031 | 0.051 | 0.067 | 0.091 | 0.105 | 0.182 | 0.253 |
| pgmpy devᵃ | 80.4 | 156 | 179 | 206 | 230 | 251 | 303 |

- ᵃ random forest (pgmpy default); a different test from FastCIT (linear)

### R, χ², sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.013 | 0.013 | 0.016 | 0.024 | 0.049 | 0.118 | 0.371 |
| bnlearnᵃᵇ | 0.082 | 0.086 | 0.092 | 0.114 | 0.187 | 0.392 | 1.10 |
| Rfastᵃ | 0.0091* | 0.0095* | 0.012* | 0.018* | 0.039* | 0.101* | 0.312 |

- ᵃ Uses the nominal degrees of freedom. FastCIT uses the adjusted degrees of freedom.
- ᵇ bnlearn ci.test() checks the whole data frame in each call. The benchmark gives it only the columns of the query.
- \* Some queries raised an error or returned NaN. The median uses the other queries. Rfast at 100: 4 of 20 queries left out; Rfast at 300: 3 of 20 queries left out; Rfast at 1 000: 1 of 20 queries left out; Rfast at 3 000: 1 of 20 queries left out; Rfast at 10 000: 1 of 20 queries left out; Rfast at 30 000: 1 of 20 queries left out.

### R, χ², conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.012 | 0.017 | 0.018 | 0.021 | 0.027 | 0.042 | 0.050 |
| bnlearnᵃᵇ | 0.073 | 0.093 | 0.107 | 0.124 | 0.149 | 0.304 | 0.965 |
| Rfastᵃ | 0.0095 | 0.012* | 0.013* | —§ | —§ | —§ | —§ |

- ᵃ Uses the nominal degrees of freedom. FastCIT uses the adjusted degrees of freedom.
- ᵇ bnlearn ci.test() checks the whole data frame in each call. The benchmark gives it only the columns of the query.
- § No result. Every query raised an error or returned NaN, or fewer than half of them gave a value. Rfast at 3: 14 of 20 queries gave NaN or an error; Rfast at 4: 19 of 20 queries gave NaN or an error.
- \* Some queries raised an error or returned NaN. The median uses the other queries. Rfast at 1: 1 of 20 queries left out; Rfast at 2: 8 of 20 queries left out.

### R, G², sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.013 | 0.014 | 0.017 | 0.024 | 0.048 | 0.118 | 0.369 |
| pcalgᵃᵇ | 0.056 | 0.149 | 0.299 | 0.724 | 2.94 | 6.91 | 23.5 |
| bnlearnᵇᶜ | 0.082 | 0.085 | 0.092 | 0.112 | 0.185 | 0.385 | 1.10 |
| Rfastᵇ | 0.0093 | 0.0098 | 0.012 | 0.018 | 0.040 | 0.101 | 0.313 |

- ᵃ pcalg returns p = 1 without running the test when n < 10 x the degrees of freedom. This happens at small n and at large |Z|, so these times are not comparable.
- ᵇ Uses the nominal degrees of freedom. FastCIT uses the adjusted degrees of freedom.
- ᶜ bnlearn ci.test() checks the whole data frame in each call. The benchmark gives it only the columns of the query.

### R, G², conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.012 | 0.017 | 0.017 | 0.019 | 0.022 | 0.035 | 0.043 |
| pcalgᵃᵇ | 0.164 | 0.298 | 0.525 | 0.892 | 0.138 | 0.122 | 0.121 |
| bnlearnᵇᶜ | 0.074 | 0.092 | 0.108 | 0.124 | 0.149 | 0.309 | 0.993 |
| Rfastᵇ | 0.0098 | 0.012 | 0.014 | 0.015 | 0.021 | 0.059 | 0.280 |

- ᵃ pcalg returns p = 1 without running the test when n < 10 x the degrees of freedom. This happens at small n and at large |Z|, so these times are not comparable.
- ᵇ Uses the nominal degrees of freedom. FastCIT uses the adjusted degrees of freedom.
- ᶜ bnlearn ci.test() checks the whole data frame in each call. The benchmark gives it only the columns of the query.

### R, Cressie-Read, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.013 | 0.014 | 0.017 | 0.024 | 0.049 | 0.118 | 0.366 |

### R, Cressie-Read, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.012 | 0.017 | 0.018 | 0.021 | 0.027 | 0.041 | 0.048 |

### R, Freeman-Tukey, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.013 | 0.014 | 0.017 | 0.024 | 0.050 | 0.118 | 0.368 |

### R, Freeman-Tukey, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.011 | 0.017 | 0.018 | 0.020 | 0.027 | 0.042 | 0.047 |

### R, Modified log-likelihood, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.012 | 0.013 | 0.016 | 0.023 | 0.049 | 0.117 | 0.368 |

### R, Modified log-likelihood, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.012 | 0.016 | 0.016 | 0.018 | 0.022 | 0.035 | 0.042 |

### R, Fisher-z, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCITᵃ | 0.010 | 0.011 | 0.011 | 0.011 | 0.010 | 0.011 | 0.011 |
| pcalgᵃ | 0.010 | 0.010 | 0.010 | 0.010 | 0.0098 | 0.0098 | 0.010 |
| bnlearnᵃᵇ | 0.053 | 0.057 | 0.071 | 0.111 | 0.246 | 0.632 | 1.97 |

- ᵃ The time does not include the one-time setup. FastCIT builds the correlation matrix in its first call, and the median leaves that call out, so its time stays flat as n grows. pcalg builds it at setup and stays flat too. bnlearn and ppcor build it in every call, so their time grows with n.
- ᵇ bnlearn ci.test() checks the whole data frame in each call. The benchmark gives it only the columns of the query.

### R, Fisher-z, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCITᵃ | 0.010 | 0.011 | 0.011 | 0.011 | 0.011 | 0.012 | 0.012 |
| pcalgᵃ | 0.0088 | 0.010 | 0.027 | 0.029 | 0.031 | 0.034 | 0.037 |
| bnlearnᵃᵇ | 0.056 | 0.071 | 0.081 | 0.091 | 0.103 | 0.130 | 0.161 |

- ᵃ The time does not include the one-time setup. FastCIT builds the correlation matrix in its first call, and the median leaves that call out, so its time stays flat as n grows. pcalg builds it at setup and stays flat too. bnlearn and ppcor build it in every call, so their time grows with n.
- ᵇ bnlearn ci.test() checks the whole data frame in each call. The benchmark gives it only the columns of the query.

### R, Pearson t, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCITᵃ | 0.011 | 0.011 | 0.011 | 0.011 | 0.011 | 0.011 | 0.011 |
| bnlearnᵃᵇ | 0.054 | 0.058 | 0.071 | 0.111 | 0.246 | 0.635 | 1.97 |
| ppcorᵃᶜ | 0.273 | 0.276 | 0.296 | 0.343 | 0.500 | 0.955 | 2.49 |

- ᵃ The time does not include the one-time setup. FastCIT builds the correlation matrix in its first call, and the median leaves that call out, so its time stays flat as n grows. pcalg builds it at setup and stays flat too. bnlearn and ppcor build it in every call, so their time grows with n.
- ᵇ bnlearn ci.test() checks the whole data frame in each call. The benchmark gives it only the columns of the query.
- ᶜ ppcor needs at least one conditioning variable. For a query with an empty set, the benchmark calls stats::cor.test, which runs the same t-test.

### R, Pearson t, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCITᵃ | 0.011 | 0.011 | 0.011 | 0.011 | 0.011 | 0.012 | 0.012 |
| bnlearnᵃᵇ | 0.057 | 0.071 | 0.081 | 0.091 | 0.103 | 0.132 | 0.162 |
| ppcorᵃᶜ | 0.072 | 0.291 | 0.310 | 0.329 | 0.345 | 0.387 | 0.432 |

- ᵃ The time does not include the one-time setup. FastCIT builds the correlation matrix in its first call, and the median leaves that call out, so its time stays flat as n grows. pcalg builds it at setup and stays flat too. bnlearn and ppcor build it in every call, so their time grows with n.
- ᵇ bnlearn ci.test() checks the whole data frame in each call. The benchmark gives it only the columns of the query.
- ᶜ ppcor needs at least one conditioning variable. For a query with an empty set, the benchmark calls stats::cor.test, which runs the same t-test.

### R, Pearson equivalence, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCITᵃ | 0.011 | 0.011 | 0.011 | 0.011 | 0.011 | 0.011 | 0.011 |

- ᵃ The time does not include the one-time setup. FastCIT builds the correlation matrix in its first call, and the median leaves that call out, so its time stays flat as n grows. pcalg builds it at setup and stays flat too. bnlearn and ppcor build it in every call, so their time grows with n.

### R, Pearson equivalence, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCITᵃ | 0.010 | 0.011 | 0.011 | 0.011 | 0.011 | 0.012 | 0.012 |

- ᵃ The time does not include the one-time setup. FastCIT builds the correlation matrix in its first call, and the median leaves that call out, so its time stays flat as n grows. pcalg builds it at setup and stays flat too. bnlearn and ppcor build it in every call, so their time grows with n.

### R, HSIC, sample size (Z empty)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.143 | 1.21 | 13.3 | 173 | 2 184 | —¶ | —¶ |
| dHSICᵃ | 0.607 | 4.75 | 54.7 | 636 | 5 440 | —¶ | —¶ |

- ᵃ Different null approximation or kernel width rule from FastCIT.
- ¶ No result. The sweep does not run this test at this sample size. The packages need too much memory there.

### R, KCI, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 1.23 | 12.3 | 287 | 8 930† | —‡ | —‡ | —‡ |

- † The first pass took more than 60 s. The cell comes from one pass. Larger points, if any, are missing.
- ‡ No result. The engine skipped this point after it passed the time budget.

### R, KCI, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 22.0 | 291 | 307 | 316 | 320 | 327 | 336 |

### R, GCM, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.014 | 0.021 | 0.042 | 0.107 | 0.324 | 0.934 | 3.11 |
| comets | 0.690 | 1.000 | 2.01 | 4.88 | 14.9 | 45.7 | 165 |

### R, GCM, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.031 | 0.042 | 0.055 | 0.068 | 0.084 | 0.118 | 0.158 |
| comets | 2.01 | 2.00 | 2.03 | 2.05 | 2.07 | 2.12 | 2.16 |

### R, Pillai, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.017 | 0.029 | 0.068 | 0.180 | 0.542 | 1.59 | 5.29 |

### R, Pillai, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.044 | 0.068 | 0.085 | 0.110 | 0.122 | 0.207 | 0.281 |
