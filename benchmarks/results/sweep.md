# FastCIT sweep benchmark

The tables give the mean time of one test call, in milliseconds. Lower is better. Each test has one table for the sample size n and one for the conditioning-set size |Z|. Each column is one value of n or |Z|.

Each cell is the mean over the calls of a point, with the standard deviation after ±. Each package runs every query once. The first call is the warm-up call, and the mean does not include it. An engine that passes the time budget skips the larger points. HSIC and KCI do not run above their memory limit. — means no result. Other marks are explained under each table.

## Setup

- Python: Python 3.14.2, AMD Ryzen 9 7950X 16-Core Processor (32 logical CPUs), Linux 7.0.0-42-generic, 2026-11-18 12:29:17; passes per point: 1; time budget: 60 s.
  - versions: causal-learn 0.1.4.5, fastcit 0.1.0, gcastle 1.0.4, hyppo 0.5.2, pgmpy 1.1.2, pingouin 0.7.0, tigramite 5.2.10.1, numpy 2.4.1, pandas 3.0.0, scipy 1.17.0, scikit-learn 1.8.0
  - dowhy run: Python 3.11.10, 2026-11-18 13:23:32, versions: dowhy 0.14, fastcit 0.1.0, numpy 2.4.6, pandas 3.1.1, scipy 1.15.3, scikit-learn 1.9.1
  - same-interpreter FastCIT reference (gcm, n, not a table row): 0.0036, 0.0091, 0.028, 0.084, 0.274, 0.820, 2.74 ms
  - same-interpreter FastCIT reference (gcm, z, not a table row): 0.017, 0.029, 0.039, 0.053, 0.068, 0.099, 0.133 ms
- R: R version 4.5.3 (2026-03-11), AMD Ryzen 9 7950X 16-Core Processor (32 logical CPUs), Linux 7.0.0-42-generic, 2026-11-18 13:23:36; passes per point: 1; time budget: 60 s.
  - versions: fastcit 0.0.0.9000, pcalg 2.7.12, bnlearn 5.2.1, dHSIC 2.2, Rfast 2.1.5.2, ppcor 1.1, comets 0.2.3

### Python, χ², sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.0024 ± 0.00081 | 0.0027 ± 0.00064 | 0.0050 ± 0.0014 | 0.013 ± 0.0044 | 0.037 ± 0.013 | 0.112 ± 0.044 | 0.332 ± 0.115 |
| pgmpy devᵃ | 0.056 ± 0.012 | 0.054 ± 0.0092 | 0.057 ± 0.013 | 0.062 ± 0.012 | 0.073 ± 0.011 | 0.111 ± 0.013 | 0.274 ± 0.033 |
| causal-learn | 0.066 ± 0.0100 | 0.069 ± 0.0075 | 0.071 ± 0.0071 | 0.074 ± 0.0077 | 0.101 ± 0.011 | 0.177 ± 0.010 | 0.395 ± 0.012 |
| gcastleᵃ | 1.91 ± 0.438 | 1.98 ± 0.463 | 2.07 ± 0.522 | 2.18 ± 0.494 | 3.91 ± 0.463 | 5.91 ± 0.603 | 11.3 ± 0.421 |

- ᵃ pgmpy and gcastle apply the Yates correction on 2 × 2 tables and cannot turn it off. FastCIT runs without it.

### Python, χ², conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.0019 ± 0.00034 | 0.0053 ± 0.0017 | 0.0070 ± 0.0011 | 0.010 ± 0.0022 | 0.016 ± 0.0048 | 0.028 ± 0.0058 | 0.035 ± 0.0080 |
| pgmpy devᵃ | 0.052 ± 0.0088 | 0.057 ± 0.013 | 0.057 ± 0.0098 | 0.064 ± 0.014 | 0.078 ± 0.016 | 0.200 ± 0.057 | 1.32 ± 1.02 |
| causal-learn | 0.072 ± 0.0079 | 0.068 ± 0.0086 | 0.071 ± 0.0096 | 0.085 ± 0.011 | 0.092 ± 0.017 | 0.165 ± 0.027 | 0.292 ± 0.049 |
| gcastleᵃ | 0.615 ± 0.035 | 2.02 ± 0.474 | 5.80 ± 2.21 | 14.4 ± 7.16 | 36.4 ± 12.9 | 157 ± 41.1 | 283 ± 43.1 |

- ᵃ pgmpy and gcastle apply the Yates correction on 2 × 2 tables and cannot turn it off. FastCIT runs without it.

### Python, G², sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.0021 ± 0.00070 | 0.0026 ± 0.00057 | 0.0050 ± 0.0015 | 0.012 ± 0.0037 | 0.035 ± 0.012 | 0.100 ± 0.035 | 0.333 ± 0.116 |
| pgmpy devᵃ | 0.049 ± 0.012 | 0.051 ± 0.0087 | 0.054 ± 0.010 | 0.056 ± 0.0089 | 0.074 ± 0.011 | 0.111 ± 0.014 | 0.250 ± 0.024 |
| causal-learn | 0.068 ± 0.0087 | 0.070 ± 0.0072 | 0.069 ± 0.0086 | 0.078 ± 0.0083 | 0.100 ± 0.0071 | 0.167 ± 0.0076 | 0.416 ± 0.016 |
| gcastleᵃ | 1.88 ± 0.418 | 1.96 ± 0.463 | 2.00 ± 0.456 | 2.12 ± 0.475 | 2.50 ± 0.490 | 3.50 ± 0.541 | 13.1 ± 0.450 |
| tigramite | 0.250 ± 0.035 | 0.278 ± 0.026 | 0.425 ± 0.092 | 0.698 ± 0.128 | 1.65 ± 0.315 | 4.33 ± 0.915 | 16.2 ± 4.66 |

- ᵃ pgmpy and gcastle apply the Yates correction on 2 × 2 tables and cannot turn it off. FastCIT runs without it.

### Python, G², conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.0015 ± 0.00020 | 0.0049 ± 0.0014 | 0.0065 ± 0.00071 | 0.0087 ± 0.0017 | 0.012 ± 0.0029 | 0.022 ± 0.0042 | 0.032 ± 0.0083 |
| pgmpy devᵃ | 0.048 ± 0.010 | 0.055 ± 0.0091 | 0.054 ± 0.0082* | 0.059 ± 0.0069* | —§ | —§ | —§ |
| causal-learn | 0.053 ± 0.0072 | 0.071 ± 0.011 | 0.077 ± 0.011 | 0.082 ± 0.0097 | 0.097 ± 0.017 | 0.172 ± 0.030 | 0.317 ± 0.052 |
| gcastleᵃ | 0.613 ± 0.040 | 2.08 ± 0.488 | 5.92 ± 2.16 | 14.5 ± 7.12 | 37.0 ± 13.0 | 157 ± 40.7 | 281 ± 41.8 |
| tigramite | 0.288 ± 0.024 | 0.370 ± 0.033 | 0.577 ± 0.106 | 0.948 ± 0.334 | 2.02 ± 0.615 | 11.1 ± 3.20 | 62.9 ± 46.3 |

- ᵃ pgmpy and gcastle apply the Yates correction on 2 × 2 tables and cannot turn it off. FastCIT runs without it.
- § No result. Every query raised an error or returned NaN, or fewer than half of them gave a value. pgmpy dev at 4: 17 of 20 queries gave NaN or an error.
- \* Some queries raised an error or returned NaN. The mean uses the other queries. pgmpy dev at 2: 2 of 20 queries left out; pgmpy dev at 3: 4 of 20 queries left out.

### Python, Cressie-Read, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.0023 ± 0.00068 | 0.0028 ± 0.00066 | 0.0052 ± 0.0014 | 0.012 ± 0.0037 | 0.036 ± 0.012 | 0.102 ± 0.036 | 0.328 ± 0.116 |
| pgmpy devᵃ | 0.055 ± 0.011 | 0.056 ± 0.011 | 0.055 ± 0.0093 | 0.059 ± 0.010 | 0.077 ± 0.012 | 0.108 ± 0.012 | 0.245 ± 0.024 |
| gcastleᵃ | 1.93 ± 0.437 | 2.02 ± 0.497 | 2.02 ± 0.477 | 2.15 ± 0.482 | 2.49 ± 0.490 | 3.43 ± 0.496 | 13.1 ± 0.396 |

- ᵃ pgmpy and gcastle apply the Yates correction on 2 × 2 tables and cannot turn it off. FastCIT runs without it.

### Python, Cressie-Read, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.0017 ± 0.00034 | 0.0051 ± 0.0014 | 0.0072 ± 0.0011 | 0.010 ± 0.0029 | 0.016 ± 0.0046 | 0.029 ± 0.0062 | 0.036 ± 0.0079 |
| pgmpy devᵃ | 0.055 ± 0.0097 | 0.055 ± 0.0090 | 0.058 ± 0.0086 | 0.067 ± 0.015 | 0.087 ± 0.022 | 0.252 ± 0.075 | 1.80 ± 1.40 |
| gcastleᵃ | 0.617 ± 0.030 | 2.01 ± 0.464 | 5.64 ± 2.06 | 14.4 ± 7.15 | 36.5 ± 12.9 | 156 ± 40.5 | 276 ± 42.0 |

- ᵃ pgmpy and gcastle apply the Yates correction on 2 × 2 tables and cannot turn it off. FastCIT runs without it.

### Python, Freeman-Tukey, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.0023 ± 0.00062 | 0.0029 ± 0.00068 | 0.0052 ± 0.0013 | 0.012 ± 0.0037 | 0.035 ± 0.012 | 0.106 ± 0.037 | 0.328 ± 0.113 |
| pgmpy devᵃ | —§ | 0.055 ± 0.0090* | 0.056 ± 0.011* | 0.061 ± 0.011* | 0.077 ± 0.014* | 0.107 ± 0.010* | 0.243 ± 0.021 |
| gcastleᵃ | —§ | 1.78 ± 0.511* | 1.94 ± 0.484* | 2.08 ± 0.491* | 2.37 ± 0.473* | 3.35 ± 0.490* | 12.9 ± 0.442 |

- ᵃ pgmpy and gcastle apply the Yates correction on 2 × 2 tables and cannot turn it off. FastCIT runs without it.
- § No result. Every query raised an error or returned NaN, or fewer than half of them gave a value. pgmpy dev at 100: 12 of 20 queries gave NaN or an error; gcastle at 100: 12 of 20 queries gave NaN or an error.
- \* Some queries raised an error or returned NaN. The mean uses the other queries. pgmpy dev at 300: 9 of 20 queries left out; pgmpy dev at 1 000: 4 of 20 queries left out; pgmpy dev at 3 000: 3 of 20 queries left out; pgmpy dev at 10 000: 2 of 20 queries left out; pgmpy dev at 30 000: 1 of 20 queries left out; gcastle at 300: 9 of 20 queries left out; gcastle at 1 000: 4 of 20 queries left out; gcastle at 3 000: 3 of 20 queries left out; gcastle at 10 000: 2 of 20 queries left out; gcastle at 30 000: 1 of 20 queries left out.

### Python, Freeman-Tukey, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.0016 ± 0.00032 | 0.0051 ± 0.0013 | 0.0070 ± 0.0010 | 0.010 ± 0.0022 | 0.016 ± 0.0049 | 0.031 ± 0.0067 | 0.036 ± 0.0083 |
| pgmpy devᵃ | 0.052 ± 0.0091 | 0.056 ± 0.011* | —§ | —§ | —§ | —§ | —§ |
| gcastleᵃ | 0.615 ± 0.042 | 1.93 ± 0.484* | —§ | —§ | —§ | —§ | —§ |

- ᵃ pgmpy and gcastle apply the Yates correction on 2 × 2 tables and cannot turn it off. FastCIT runs without it.
- § No result. Every query raised an error or returned NaN, or fewer than half of them gave a value. pgmpy dev at 2: 15 of 20 queries gave NaN or an error; pgmpy dev at 3: 18 of 20 queries gave NaN or an error; pgmpy dev at 4: 19 of 20 queries gave NaN or an error; pgmpy dev at 6: 19 of 20 queries gave NaN or an error; pgmpy dev at 8: 17 of 20 queries gave NaN or an error; gcastle at 2: 15 of 20 queries gave NaN or an error; gcastle at 3: 18 of 20 queries gave NaN or an error; gcastle at 4: 19 of 20 queries gave NaN or an error; gcastle at 6: 19 of 20 queries gave NaN or an error; gcastle at 8: 17 of 20 queries gave NaN or an error.
- \* Some queries raised an error or returned NaN. The mean uses the other queries. pgmpy dev at 1: 4 of 20 queries left out; gcastle at 1: 4 of 20 queries left out.

### Python, Modified log-likelihood, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.0019 ± 0.00058 | 0.0026 ± 0.00056 | 0.0049 ± 0.0014 | 0.012 ± 0.0039 | 0.035 ± 0.012 | 0.101 ± 0.036 | 0.326 ± 0.115 |
| pgmpy devᵃ | 0.048 ± 0.016 | 0.048 ± 0.011 | 0.053 ± 0.011 | 0.055 ± 0.0095 | 0.070 ± 0.011 | 0.106 ± 0.012 | 0.240 ± 0.021 |
| gcastleᵃ | 1.89 ± 0.429 | 2.03 ± 0.458 | 2.03 ± 0.471 | 2.10 ± 0.468 | 2.43 ± 0.463 | 3.62 ± 0.482 | 13.1 ± 0.489 |

- ᵃ pgmpy and gcastle apply the Yates correction on 2 × 2 tables and cannot turn it off. FastCIT runs without it.

### Python, Modified log-likelihood, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.0015 ± 0.00031 | 0.0049 ± 0.0013 | 0.0063 ± 0.00064 | 0.0080 ± 0.0015 | 0.012 ± 0.0031 | 0.022 ± 0.0040 | 0.034 ± 0.0099 |
| pgmpy devᵃ | 0.050 ± 0.0078 | 0.052 ± 0.0095 | 0.049 ± 0.0094* | 0.052 ± 0.011* | —§ | —§ | —§ |
| gcastleᵃ | 0.614 ± 0.032 | 2.01 ± 0.466 | 5.74 ± 2.14 | 14.4 ± 7.11 | 36.7 ± 13.0 | 157 ± 40.4 | 277 ± 42.2 |

- ᵃ pgmpy and gcastle apply the Yates correction on 2 × 2 tables and cannot turn it off. FastCIT runs without it.
- § No result. Every query raised an error or returned NaN, or fewer than half of them gave a value. pgmpy dev at 4: 17 of 20 queries gave NaN or an error.
- \* Some queries raised an error or returned NaN. The mean uses the other queries. pgmpy dev at 2: 2 of 20 queries left out; pgmpy dev at 3: 4 of 20 queries left out.

### Python, Fisher-z, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCITᵃ | 0.00056 ± 0.00022 | 0.00061 ± 0.00014 | 0.00064 ± 0.00023 | 0.00068 ± 0.00020 | 0.00076 ± 0.00034 | 0.00077 ± 0.00040 | 0.0011 ± 0.0013 |
| pgmpy devᵃ | 0.408 ± 0.033 | 0.405 ± 0.026 | 0.424 ± 0.023 | 0.475 ± 0.027 | 0.649 ± 0.029 | 1.13 ± 0.035 | 2.73 ± 0.035 |
| causal-learnᵃ | 0.036 ± 0.0076 | 0.034 ± 0.0050 | 0.033 ± 0.0056 | 0.033 ± 0.0049 | 0.034 ± 0.0053 | 0.034 ± 0.0081 | 0.033 ± 0.0063 |
| gcastleᵃ | 0.055 ± 0.0092 | 0.055 ± 0.0084 | 0.060 ± 0.0086 | 0.074 ± 0.0095 | 0.114 ± 0.012 | 0.218 ± 0.019 | 0.580 ± 0.027 |

- ᵃ The time does not include the one-time setup or the first call. FastCIT builds the correlation matrix in its first call, so its time stays flat as n grows. causal-learn builds it at setup and stays flat too. pgmpy and pingouin build it in every call, so their time grows with n.

### Python, Fisher-z, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCITᵃ | 0.00056 ± 0.00022 | 0.00061 ± 0.00016 | 0.0012 ± 0.00047 | 0.00072 ± 0.00021 | 0.00081 ± 0.00020 | 0.0012 ± 0.00053 | 0.0014 ± 0.00052 |
| pgmpy devᵃ | 0.220 ± 0.028 | 0.424 ± 0.027 | 0.447 ± 0.042 | 0.454 ± 0.030 | 0.468 ± 0.026 | 0.490 ± 0.030 | 0.518 ± 0.025 |
| causal-learnᵃ | 0.031 ± 0.0047 | 0.034 ± 0.0068 | 0.033 ± 0.0046 | 0.034 ± 0.0050 | 0.034 ± 0.0056 | 0.035 ± 0.0058 | 0.038 ± 0.0065 |
| gcastleᵃ | 0.049 ± 0.0074 | 0.060 ± 0.0080 | 0.059 ± 0.0090 | 0.065 ± 0.0096 | 0.064 ± 0.0091 | 0.066 ± 0.011 | 0.076 ± 0.012 |

- ᵃ The time does not include the one-time setup or the first call. FastCIT builds the correlation matrix in its first call, so its time stays flat as n grows. causal-learn builds it at setup and stays flat too. pgmpy and pingouin build it in every call, so their time grows with n.

### Python, Pearson t, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCITᵃ | 0.00074 ± 0.00016 | 0.00074 ± 0.00017 | 0.00083 ± 0.00019 | 0.00082 ± 0.00024 | 0.00085 ± 0.00033 | 0.00089 ± 0.00032 | 0.0011 ± 0.00079 |
| pgmpy devᵃ | 0.362 ± 0.028 | 0.371 ± 0.033 | 0.388 ± 0.036 | 0.450 ± 0.028 | 0.612 ± 0.030 | 1.11 ± 0.045 | 2.71 ± 0.071 |
| tigramiteᵃ | 0.310 ± 0.024 | 0.332 ± 0.022 | 0.389 ± 0.022 | 0.563 ± 0.027 | 1.14 ± 0.020 | 3.11 ± 0.019 | 9.83 ± 0.016 |
| pingouinᵃ | 1.41 ± 0.051 | 1.42 ± 0.035 | 1.46 ± 0.031 | 1.61 ± 0.025 | 2.00 ± 0.025 | 3.04 ± 0.229 | 8.25 ± 0.611 |

- ᵃ The time does not include the one-time setup or the first call. FastCIT builds the correlation matrix in its first call, so its time stays flat as n grows. causal-learn builds it at setup and stays flat too. pgmpy and pingouin build it in every call, so their time grows with n.

### Python, Pearson t, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCITᵃ | 0.00063 ± 0.00020 | 0.00081 ± 0.00017 | 0.00087 ± 0.00026 | 0.00088 ± 0.00034 | 0.00091 ± 0.00019 | 0.0014 ± 0.00042 | 0.0015 ± 0.00039 |
| pgmpy devᵃ | 0.178 ± 0.023 | 0.385 ± 0.026 | 0.394 ± 0.028 | 0.411 ± 0.027 | 0.432 ± 0.027 | 0.453 ± 0.031 | 0.480 ± 0.028 |
| tigramiteᵃ | 0.324 ± 0.022 | 0.386 ± 0.025 | 0.419 ± 0.024 | 0.443 ± 0.019 | 0.478 ± 0.027 | 0.523 ± 0.019 | 0.573 ± 0.022 |
| pingouinᵃ | 1.36 ± 0.021 | 1.45 ± 0.022 | 1.53 ± 0.025 | 1.62 ± 0.024 | 1.71 ± 0.027 | 1.87 ± 0.029 | 2.02 ± 0.020 |

- ᵃ The time does not include the one-time setup or the first call. FastCIT builds the correlation matrix in its first call, so its time stays flat as n grows. causal-learn builds it at setup and stays flat too. pgmpy and pingouin build it in every call, so their time grows with n.

### Python, Pearson equivalence, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCITᵃ | 0.00065 ± 0.00019 | 0.00059 ± 0.00014 | 0.00064 ± 0.00017 | 0.00070 ± 0.00023 | 0.00072 ± 0.00022 | 0.00069 ± 0.00024 | 0.00100 ± 0.00043 |
| pgmpy devᵃ | 0.431 ± 0.028 | 0.436 ± 0.031 | 0.456 ± 0.029 | 0.513 ± 0.035 | 0.696 ± 0.041 | 1.18 ± 0.037 | 2.80 ± 0.054 |

- ᵃ The time does not include the one-time setup or the first call. FastCIT builds the correlation matrix in its first call, so its time stays flat as n grows. causal-learn builds it at setup and stays flat too. pgmpy and pingouin build it in every call, so their time grows with n.

### Python, Pearson equivalence, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCITᵃ | 0.00053 ± 0.00016 | 0.00064 ± 0.00014 | 0.00073 ± 0.00017 | 0.00073 ± 0.00020 | 0.00084 ± 0.00026 | 0.0013 ± 0.00051 | 0.0015 ± 0.00059 |
| pgmpy devᵃ | 0.244 ± 0.034 | 0.473 ± 0.037 | 0.497 ± 0.044 | 0.488 ± 0.039 | 0.491 ± 0.033 | 0.523 ± 0.031 | 0.557 ± 0.033 |

- ᵃ The time does not include the one-time setup or the first call. FastCIT builds the correlation matrix in its first call, so its time stays flat as n grows. causal-learn builds it at setup and stays flat too. pgmpy and pingouin build it in every call, so their time grows with n.

### Python, HSIC, sample size (Z empty)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.126 ± 0.0011 | 1.11 ± 0.022 | 12.2 ± 0.056 | 167 ± 1.31 | 2 152 ± 15.1 | —¶ | —¶ |
| pgmpy dev | 0.371 ± 0.018 | 0.840 ± 0.012 | 7.14 ± 0.067 | 102 ± 2.78 | 984 ± 17.9 | —¶ | —¶ |
| causal-learnᵃ | 0.345 ± 0.032 | 0.824 ± 0.031 | 7.58 ± 0.228 | 136 ± 1.96 | 1 355 ± 8.59 | —¶ | —¶ |
| hyppoᵃ | 0.622 ± 0.079 | 2.59 ± 0.118 | 41.7 ± 1.20 | 551 ± 8.06 | 6 298 ± 40.2 | —‡ | —‡ |

- ᵃ Different null approximation or kernel width rule from FastCIT.
- ‡ No result. The engine skipped this point after it passed the time budget.
- ¶ No result. The sweep does not run this test at this sample size. The packages need too much memory there.

### Python, KCI, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 1.20 ± 0.016 | 12.2 ± 0.245 | 323 ± 1.63 | 8 728 ± 187 | —‡ | —‡ | —‡ |
| pgmpy dev | 1.73 ± 0.037 | 8.06 ± 0.048 | 108 ± 0.802 | 1 506 ± 43.1 | 76 812 ± 1 214 | —‡ | —‡ |
| causal-learnᵃ | 2.13 ± 0.039 | 13.1 ± 0.122 | 176 ± 0.978 | 3 328 ± 77.1 | 192 827 ± 2 323* | —‡ | —‡ |

- ᵃ Different null approximation or kernel width rule from FastCIT.
- ‡ No result. The engine skipped this point after it passed the time budget.
- \* Some queries raised an error or returned NaN. The mean uses the other queries. causal-learn at 10 000: 1 of 10 queries left out.

### Python, KCI, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 9.56 ± 0.255 | 324 ± 3.20 | 346 ± 4.21 | 351 ± 2.47 | 356 ± 0.774 | 363 ± 1.56 | 370 ± 1.02 |
| pgmpy dev | 11.3 ± 7.32 | 109 ± 0.454 | 111 ± 0.504 | 116 ± 0.801 | 120 ± 0.417 | 120 ± 0.363 | 122 ± 0.395 |
| causal-learnᵃ | 7.69 ± 0.216 | 178 ± 0.929 | 185 ± 3.24 | 203 ± 3.34 | 220 ± 2.14 | 219 ± 0.808 | 222 ± 1.32 |

- ᵃ Different null approximation or kernel width rule from FastCIT.

### Python, GCM, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.0035 ± 0.00028 | 0.0092 ± 0.00035 | 0.028 ± 0.0011 | 0.084 ± 0.0015 | 0.277 ± 0.0066 | 0.840 ± 0.015 | 2.80 ± 0.042 |
| pgmpy dev | 2.25 ± 0.066 | 2.28 ± 0.016 | 2.24 ± 0.044 | 2.32 ± 0.053 | 2.56 ± 0.069 | 3.23 ± 0.034 | 5.30 ± 0.025 |
| dowhy | 0.622 ± 0.041 | 0.613 ± 0.019 | 0.636 ± 0.022 | 0.721 ± 0.029 | 0.975 ± 0.027 | 1.70 ± 0.035 | 4.19 ± 0.090 |

### Python, GCM, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.018 ± 0.00048 | 0.028 ± 0.0013 | 0.039 ± 0.0017 | 0.053 ± 0.0013 | 0.067 ± 0.0047 | 0.099 ± 0.0025 | 0.134 ± 0.0057 |
| pgmpy dev | 2.21 ± 0.037 | 2.28 ± 0.049 | 2.31 ± 0.042 | 2.31 ± 0.058 | 2.32 ± 0.050 | 2.39 ± 0.058 | 2.47 ± 0.033 |
| dowhy | 0.060 ± 0.0068 | 0.651 ± 0.021 | 0.717 ± 0.028 | 0.765 ± 0.025 | 0.796 ± 0.019 | 0.890 ± 0.021 | 0.983 ± 0.031 |

### Python, Pillai, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.0067 ± 0.0015 | 0.016 ± 0.0038 | 0.049 ± 0.012 | 0.147 ± 0.037 | 0.480 ± 0.122 | 1.44 ± 0.363 | 4.80 ± 1.18 |
| pgmpy devᵃ | 82.0 ± 10.3 | 93.4 ± 15.5 | 137 ± 50.8 | 306 ± 200 | 1 109 ± 927 | 4 191 ± 3 834 | —‡ |

- ᵃ random forest (pgmpy default); a different test from FastCIT (linear)
- ‡ No result. The engine skipped this point after it passed the time budget.

### Python, Pillai, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.032 ± 0.0095 | 0.049 ± 0.012 | 0.071 ± 0.018 | 0.100 ± 0.025 | 0.114 ± 0.024 | 0.196 ± 0.024 | 0.260 ± 0.025 |
| pgmpy devᵃ | 85.8 ± 10.4 | 138 ± 51.5 | 173 ± 48.5 | 217 ± 30.0 | 243 ± 44.1 | 259 ± 64.8 | 305 ± 66.6 |

- ᵃ random forest (pgmpy default); a different test from FastCIT (linear)

### R, χ², sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.013 ± 0.0018 | 0.014 ± 0.0016 | 0.017 ± 0.0026 | 0.023 ± 0.0044 | 0.045 ± 0.013 | 0.105 ± 0.035 | 0.355 ± 0.141 |
| bnlearnᵃᵇ | 0.088 ± 0.013 | 0.088 ± 0.0050 | 0.097 ± 0.0069 | 0.117 ± 0.0078 | 0.188 ± 0.0076 | 0.397 ± 0.014 | 1.11 ± 0.039 |
| Rfastᵃ | 0.0098 ± 0.0011* | 0.010 ± 0.0012* | 0.013 ± 0.0022* | 0.019 ± 0.0016* | 0.040 ± 0.0021* | 0.103 ± 0.0040* | 0.330 ± 0.0066 |

- ᵃ Uses the nominal degrees of freedom. FastCIT uses the adjusted degrees of freedom.
- ᵇ bnlearn ci.test() checks the whole data frame in each call. The benchmark gives it only the columns of the query.
- \* Some queries raised an error or returned NaN. The mean uses the other queries. Rfast at 100: 4 of 20 queries left out; Rfast at 300: 3 of 20 queries left out; Rfast at 1 000: 1 of 20 queries left out; Rfast at 3 000: 1 of 20 queries left out; Rfast at 10 000: 1 of 20 queries left out; Rfast at 30 000: 1 of 20 queries left out.

### R, χ², conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.012 ± 0.0015 | 0.017 ± 0.0024 | 0.019 ± 0.0027 | 0.022 ± 0.0041 | 0.028 ± 0.0064 | 0.042 ± 0.0070 | 0.053 ± 0.010 |
| bnlearnᵃᵇ | 0.077 ± 0.0061 | 0.096 ± 0.0075 | 0.114 ± 0.011 | 0.132 ± 0.017 | 0.153 ± 0.023 | 0.305 ± 0.062 | 1.27 ± 0.794 |
| Rfastᵃ | 0.010 ± 0.0013 | 0.013 ± 0.0020* | 0.014 ± 0.00071* | —§ | —§ | —§ | —§ |

- ᵃ Uses the nominal degrees of freedom. FastCIT uses the adjusted degrees of freedom.
- ᵇ bnlearn ci.test() checks the whole data frame in each call. The benchmark gives it only the columns of the query.
- § No result. Every query raised an error or returned NaN, or fewer than half of them gave a value. Rfast at 3: 14 of 20 queries gave NaN or an error; Rfast at 4: 19 of 20 queries gave NaN or an error.
- \* Some queries raised an error or returned NaN. The mean uses the other queries. Rfast at 1: 1 of 20 queries left out; Rfast at 2: 8 of 20 queries left out.

### R, G², sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.013 ± 0.0013 | 0.015 ± 0.0026 | 0.017 ± 0.0025 | 0.024 ± 0.0048 | 0.044 ± 0.013 | 0.105 ± 0.035 | 0.323 ± 0.114 |
| pcalgᵃᵇ | 0.074 ± 0.036 | 0.149 ± 0.027 | 0.300 ± 0.058 | 0.719 ± 0.158 | 3.47 ± 1.33 | 7.78 ± 2.60 | 28.5 ± 8.43 |
| bnlearnᵇᶜ | 0.086 ± 0.0088 | 0.091 ± 0.0087 | 0.097 ± 0.0095 | 0.118 ± 0.0082 | 0.188 ± 0.010 | 0.400 ± 0.016 | 1.11 ± 0.061 |
| Rfastᵇ | 0.010 ± 0.0015 | 0.010 ± 0.0013 | 0.013 ± 0.0020 | 0.019 ± 0.0014 | 0.040 ± 0.0019 | 0.103 ± 0.0030 | 0.319 ± 0.0087 |

- ᵃ pcalg returns p = 1 without running the test when n < 10 x the degrees of freedom. This happens at small n and at large |Z|, so these times are not comparable.
- ᵇ Uses the nominal degrees of freedom. FastCIT uses the adjusted degrees of freedom.
- ᶜ bnlearn ci.test() checks the whole data frame in each call. The benchmark gives it only the columns of the query.

### R, G², conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.012 ± 0.0013 | 0.016 ± 0.0022 | 0.019 ± 0.0017 | 0.022 ± 0.0033 | 0.023 ± 0.0046 | 0.036 ± 0.0050 | 0.046 ± 0.0090 |
| pcalgᵃᵇ | 0.165 ± 0.015 | 0.298 ± 0.057 | 0.541 ± 0.209 | 0.746 ± 0.456 | 0.529 ± 0.688 | 0.123 ± 0.0049 | 0.127 ± 0.0047 |
| bnlearnᵇᶜ | 0.078 ± 0.010 | 0.097 ± 0.0081 | 0.110 ± 0.0072 | 0.131 ± 0.024 | 0.155 ± 0.022 | 0.306 ± 0.065 | 1.32 ± 0.871 |
| Rfastᵇ | 0.010 ± 0.0013 | 0.012 ± 0.0012 | 0.014 ± 0.0017 | 0.018 ± 0.0047 | 0.024 ± 0.0084 | 0.060 ± 0.020 | 0.369 ± 0.292 |

- ᵃ pcalg returns p = 1 without running the test when n < 10 x the degrees of freedom. This happens at small n and at large |Z|, so these times are not comparable.
- ᵇ Uses the nominal degrees of freedom. FastCIT uses the adjusted degrees of freedom.
- ᶜ bnlearn ci.test() checks the whole data frame in each call. The benchmark gives it only the columns of the query.

### R, Cressie-Read, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.014 ± 0.0018 | 0.014 ± 0.0015 | 0.017 ± 0.0025 | 0.024 ± 0.0043 | 0.047 ± 0.013 | 0.104 ± 0.035 | 0.324 ± 0.114 |

### R, Cressie-Read, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.012 ± 0.0017 | 0.017 ± 0.0026 | 0.018 ± 0.0021 | 0.021 ± 0.0036 | 0.027 ± 0.0053 | 0.041 ± 0.0068 | 0.050 ± 0.0089 |

### R, Freeman-Tukey, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.013 ± 0.0018 | 0.014 ± 0.0020 | 0.016 ± 0.0023 | 0.024 ± 0.0044 | 0.048 ± 0.013 | 0.104 ± 0.034 | 0.325 ± 0.113 |

### R, Freeman-Tukey, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.012 ± 0.0015 | 0.017 ± 0.0031 | 0.018 ± 0.0018 | 0.021 ± 0.0030 | 0.027 ± 0.0052 | 0.041 ± 0.0067 | 0.050 ± 0.0098 |

### R, Modified log-likelihood, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.013 ± 0.0019 | 0.014 ± 0.0021 | 0.017 ± 0.0025 | 0.023 ± 0.0046 | 0.044 ± 0.012 | 0.105 ± 0.036 | 0.325 ± 0.115 |

### R, Modified log-likelihood, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.012 ± 0.0011 | 0.016 ± 0.0023 | 0.017 ± 0.0019 | 0.019 ± 0.0021 | 0.023 ± 0.0032 | 0.034 ± 0.0045 | 0.047 ± 0.0093 |

### R, Fisher-z, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCITᵃ | 0.011 ± 0.0015 | 0.011 ± 0.0018 | 0.011 ± 0.0012 | 0.012 ± 0.0025 | 0.012 ± 0.0031 | 0.011 ± 0.0026 | 0.013 ± 0.0063 |
| pcalgᵃ | 0.010 ± 0.0015 | 0.010 ± 0.0022 | 0.0100 ± 0.0013 | 0.0099 ± 0.00087 | 0.0099 ± 0.0010 | 0.011 ± 0.0015 | 0.011 ± 0.0026 |
| bnlearnᵃᵇ | 0.056 ± 0.0073 | 0.062 ± 0.0079 | 0.074 ± 0.0070 | 0.118 ± 0.0083 | 0.254 ± 0.010 | 0.643 ± 0.018 | 2.01 ± 0.052 |

- ᵃ The time does not include the one-time setup or the first call. FastCIT builds the correlation matrix in its first call, so its time stays flat as n grows. pcalg builds it at setup and stays flat too. bnlearn and ppcor build it in every call, so their time grows with n.
- ᵇ bnlearn ci.test() checks the whole data frame in each call. The benchmark gives it only the columns of the query.

### R, Fisher-z, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCITᵃ | 0.011 ± 0.0014 | 0.012 ± 0.0015 | 0.011 ± 0.0014 | 0.012 ± 0.0021 | 0.012 ± 0.0024 | 0.013 ± 0.0019 | 0.013 ± 0.0026 |
| pcalgᵃ | 0.0094 ± 0.0013 | 0.010 ± 0.0017 | 0.028 ± 0.0046 | 0.030 ± 0.0029 | 0.032 ± 0.0037 | 0.035 ± 0.0049 | 0.040 ± 0.0042 |
| bnlearnᵃᵇ | 0.064 ± 0.0087 | 0.074 ± 0.0063 | 0.087 ± 0.0063 | 0.095 ± 0.0074 | 0.110 ± 0.0088 | 0.133 ± 0.0090 | 0.173 ± 0.013 |

- ᵃ The time does not include the one-time setup or the first call. FastCIT builds the correlation matrix in its first call, so its time stays flat as n grows. pcalg builds it at setup and stays flat too. bnlearn and ppcor build it in every call, so their time grows with n.
- ᵇ bnlearn ci.test() checks the whole data frame in each call. The benchmark gives it only the columns of the query.

### R, Pearson t, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCITᵃ | 0.011 ± 0.0014 | 0.012 ± 0.0013 | 0.012 ± 0.0018 | 0.012 ± 0.0022 | 0.012 ± 0.0028 | 0.012 ± 0.0021 | 0.014 ± 0.0087 |
| bnlearnᵃᵇ | 0.058 ± 0.010 | 0.061 ± 0.0068 | 0.075 ± 0.0077 | 0.115 ± 0.0074 | 0.250 ± 0.0074 | 0.643 ± 0.015 | 2.01 ± 0.046 |
| ppcorᵃᶜ | 0.293 ± 0.020 | 0.291 ± 0.014 | 0.308 ± 0.013 | 0.351 ± 0.013 | 0.509 ± 0.018 | 0.970 ± 0.023 | 2.59 ± 0.081 |

- ᵃ The time does not include the one-time setup or the first call. FastCIT builds the correlation matrix in its first call, so its time stays flat as n grows. pcalg builds it at setup and stays flat too. bnlearn and ppcor build it in every call, so their time grows with n.
- ᵇ bnlearn ci.test() checks the whole data frame in each call. The benchmark gives it only the columns of the query.
- ᶜ ppcor needs at least one conditioning variable. For a query with an empty set, the benchmark calls stats::cor.test, which runs the same t-test.

### R, Pearson t, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCITᵃ | 0.013 ± 0.0032 | 0.012 ± 0.0015 | 0.012 ± 0.0016 | 0.012 ± 0.0019 | 0.012 ± 0.0018 | 0.013 ± 0.0020 | 0.013 ± 0.0018 |
| bnlearnᵃᵇ | 0.062 ± 0.0090 | 0.075 ± 0.0057 | 0.084 ± 0.0079 | 0.095 ± 0.0090 | 0.106 ± 0.0075 | 0.134 ± 0.0079 | 0.168 ± 0.014 |
| ppcorᵃᶜ | 0.074 ± 0.0061 | 0.302 ± 0.012 | 0.318 ± 0.018 | 0.338 ± 0.016 | 0.354 ± 0.012 | 0.393 ± 0.015 | 0.439 ± 0.020 |

- ᵃ The time does not include the one-time setup or the first call. FastCIT builds the correlation matrix in its first call, so its time stays flat as n grows. pcalg builds it at setup and stays flat too. bnlearn and ppcor build it in every call, so their time grows with n.
- ᵇ bnlearn ci.test() checks the whole data frame in each call. The benchmark gives it only the columns of the query.
- ᶜ ppcor needs at least one conditioning variable. For a query with an empty set, the benchmark calls stats::cor.test, which runs the same t-test.

### R, Pearson equivalence, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCITᵃ | 0.011 ± 0.0011 | 0.011 ± 0.0010 | 0.012 ± 0.0016 | 0.012 ± 0.0022 | 0.012 ± 0.0032 | 0.012 ± 0.0020 | 0.013 ± 0.0057 |

- ᵃ The time does not include the one-time setup or the first call. FastCIT builds the correlation matrix in its first call, so its time stays flat as n grows. pcalg builds it at setup and stays flat too. bnlearn and ppcor build it in every call, so their time grows with n.

### R, Pearson equivalence, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCITᵃ | 0.011 ± 0.0015 | 0.012 ± 0.0015 | 0.012 ± 0.0020 | 0.012 ± 0.0025 | 0.013 ± 0.0018 | 0.013 ± 0.0014 | 0.013 ± 0.0020 |

- ᵃ The time does not include the one-time setup or the first call. FastCIT builds the correlation matrix in its first call, so its time stays flat as n grows. pcalg builds it at setup and stays flat too. bnlearn and ppcor build it in every call, so their time grows with n.

### R, HSIC, sample size (Z empty)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.145 ± 0.0025 | 1.22 ± 0.0073 | 13.5 ± 0.073 | 195 ± 0.423 | 2 205 ± 8.83 | —¶ | —¶ |
| dHSICᵃ | 0.623 ± 0.018 | 4.82 ± 0.052 | 56.5 ± 4.27 | 627 ± 2.44 | 5 531 ± 91.8 | —¶ | —¶ |

- ᵃ Different null approximation or kernel width rule from FastCIT.
- ¶ No result. The sweep does not run this test at this sample size. The packages need too much memory there.

### R, KCI, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 1.22 ± 0.011 | 12.5 ± 0.182 | 290 ± 0.774 | 8 640 ± 43.5 | —‡ | —‡ | —‡ |

- ‡ No result. The engine skipped this point after it passed the time budget.

### R, KCI, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 21.0 ± 0.115 | 290 ± 0.647 | 307 ± 3.48 | 317 ± 1.39 | 322 ± 0.662 | 329 ± 1.60 | 335 ± 0.805 |

### R, GCM, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.015 ± 0.0017 | 0.022 ± 0.0013 | 0.043 ± 0.0016 | 0.110 ± 0.0049 | 0.324 ± 0.0061 | 0.953 ± 0.022 | 3.15 ± 0.039 |
| comets | 0.703 ± 0.021 | 1.01 ± 0.017 | 2.04 ± 0.048 | 4.91 ± 0.044 | 14.9 ± 0.122 | 49.0 ± 7.68 | 197 ± 56.1 |

### R, GCM, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.032 ± 0.0025 | 0.045 ± 0.0037 | 0.056 ± 0.0022 | 0.070 ± 0.0025 | 0.085 ± 0.0023 | 0.121 ± 0.0054 | 0.158 ± 0.0039 |
| comets | 2.03 ± 0.047 | 2.03 ± 0.033 | 2.07 ± 0.046 | 2.11 ± 0.072 | 2.10 ± 0.046 | 2.15 ± 0.048 | 2.19 ± 0.044 |

### R, Pillai, sample size (|Z| = 1)

| Package | 100 | 300 | 1 000 | 3 000 | 10 000 | 30 000 | 100 000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.018 ± 0.0027 | 0.029 ± 0.0048 | 0.065 ± 0.013 | 0.170 ± 0.036 | 0.533 ± 0.121 | 1.56 ± 0.373 | 5.13 ± 1.21 |

### R, Pillai, conditioning-set size (n = 1 000)

| Package | 0 | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FastCIT | 0.045 ± 0.011 | 0.065 ± 0.013 | 0.089 ± 0.019 | 0.113 ± 0.021 | 0.146 ± 0.028 | 0.213 ± 0.024 | 0.294 ± 0.023 |
