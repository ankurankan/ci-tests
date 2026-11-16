# FastCIT benchmarks

This folder holds a reproducible benchmark for FastCIT.
It compares the time of one test call in FastCIT with other packages.
It also records how closely the p-values agree.

## What the benchmark measures

The benchmark measures the time of one conditional independence test call.
It does not measure a full causal discovery run.

The scripts use the same data and the same queries for every package.
A query is one triple: variable X, variable Y, and a set of conditioning variables Z.

Each package runs three passes.
Each pass builds new test objects.
The build time is not part of the result.
Caches are off when the package has an option for it.
Each pass times every query once.
The time of a query is the best of the three passes.
The result of a test is the median of the query times, in milliseconds.

The χ² and G² tests run without the Yates correction in every package.
The exception is pgmpy.
pgmpy cannot turn the correction off.
The agreement table compares pgmpy with FastCIT with the correction on.

### Python packages

| Test | FastCIT | pgmpy dev | causal-learn | andrey-core |
|---|---|---|---|---|
| χ² | `ChiSquared` | `ChiSquare` | `chisq` | `chisq` |
| G² | `LogLikelihood` | `GSq` | `gsq` | `gsq` |
| Fisher-z | `FisherZ` | `FisherZ` | `fisherz` | `fisherz` |
| Pearson t | `PearsonCorrelation` | `Pearsonr` | none | `student_t` |
| HSIC (n = 300) | `HSIC` | `HSIC` | `kci`, empty Z | `kci`, empty Z |
| KCI (n = 300, 1 000) | `KCI` | `KCI` | `kci` | `kci` |
| GCM | `GCM` | `GCM` | none | none |
| Pillai | `PillaiTrace` | `PillaiTrace` | none | none |

The pgmpy `PillaiTrace` uses a random forest by default.
FastCIT uses a linear model.
The two tests are different, and the table marks this.

### R packages

| Test | FastCIT | pcalg | bnlearn | dHSIC |
|---|---|---|---|---|
| χ² | `chi_squared` | none | `x2` | none |
| G² | `log_likelihood` | `disCItest` | `mi` | none |
| Fisher-z | `fisher_z` | `gaussCItest` | `zf` | none |
| Pearson t | `pearson_correlation` | none | `cor` | none |
| HSIC (median width) | `hsic` | none | none | `dhsic.test` |

The pcalg G² test runs with `adaptDF = FALSE`.
The pcalg Fisher-z test gets a correlation matrix.
The script builds this matrix once, outside the timer.

## Data

`data.py` writes all data.
The data are synthetic, and the seeds are fixed.
The script downloads nothing.

| Data | Shape | Used by |
|---|---|---|
| Discrete | 30 variables with 2 to 4 levels, n = 10 000, random DAG with random tables | χ², G² |
| Gaussian | 30 variables, linear model on a random DAG, n = 10 000 | Fisher-z, Pearson t, GCM |
| Nonlinear | 8 variables with tanh, sin, square and cos links, n = 300 and n = 1 000 | HSIC, KCI |
| Mixed | 3 categorical and 3 continuous variables, n = 2 000 | Pillai |

| Group | Queries |
|---|---|
| Discrete | 50, with 0 to 3 conditioning variables |
| Gaussian | 50, with 0 to 4 conditioning variables |
| HSIC | 28, all pairs of 8 variables, n = 300 |
| KCI | 30 at n = 300 and 10 at n = 1 000, with 1 to 2 conditioning variables |
| GCM | 50, with 0 to 4 conditioning variables |
| Pillai | 40, with 0 to 2 conditioning variables |

## Install

Use Python 3.10 or newer and a recent R.
Install the Python packages with pinned versions.

```bash
pip install causal-learn==0.1.4.5 andrey-core==0.17.1 pandas numpy threadpoolctl
pip install "pgmpy @ git+https://github.com/pgmpy/pgmpy.git@a67c17d9"
```

Build FastCIT from this repository.
Note the commit of the repository in your result.

```bash
pip install ./crates/ci-python
```

You can also run `maturin build --release -m crates/ci-python/Cargo.toml` and install the wheel.

Install the R packages with pinned versions.
The pcalg package needs the Bioconductor packages `graph` and `RBGL`.

```r
install.packages(c("remotes", "BiocManager", "jsonlite"))
BiocManager::install(c("graph", "RBGL"))
remotes::install_version("bnlearn", "5.2.1")
remotes::install_version("dHSIC", "2.2")
remotes::install_version("pcalg", "2.7.12")
```

Install the FastCIT R package from this repository.

```bash
R CMD build crates/ci-r
R CMD INSTALL fastcit_*.tar.gz
```

The scripts record the installed versions, the FastCIT commit and the thread settings.
The FastCIT commit gets the suffix `-dirty` when the working tree has changes.
The scripts read the pgmpy commit from the pip metadata.
If you use a source archive, set `PGMPY_COMMIT=a67c17d9` before you run `bench_python.py`.
Without this value, the scripts record `unknown`.

## Run

Pick an output folder.
Run these commands from the repository root.

```bash
python benchmarks/data.py OUT
python benchmarks/bench_python.py OUT
Rscript benchmarks/bench_r.R OUT
python benchmarks/summarize.py OUT
```

Add `--quick` to `bench_python.py` and `bench_r.R` for a short test run.
A quick run uses 2 queries per group.

The Python run takes about 2 minutes.
The R run takes about 10 seconds.
Use a quiet machine.
Wait until the load in `uptime` is below 1.5.
Check the load with `uptime` before and after the run.
The scripts record both values.

The scripts use the default thread count of each package.
FastCIT runs on one thread.
The scripts record the BLAS libraries and their thread counts.

To publish a result, copy the files to the results folder.

```bash
cp OUT/python.json OUT/r.json OUT/summary.md benchmarks/results/
```

The `data.py` script writes CSV files.
Do not commit them.

## Results

The `results` folder holds the files of the last full run.

| File | Content |
|---|---|
| `results/python.json` | Median time, per-query times and p-values for each Python package |
| `results/r.json` | The same data for each R package |
| `results/summary.md` | Tables, run details and agreement |

`summary.md` starts with the date, CPU, operating system, package versions, commit hashes and load.

## How to read the tables

Each cell holds the median time of one test call, in milliseconds.
A lower number is better.
A dash means that the package does not offer the test.
A star means that the package raised an error or returned NaN on some queries.
The median leaves those queries out.

The total-per-pass tables show a second metric.
A pass builds the state of the package and runs all queries of the group once.
FastCIT, pcalg, causal-learn and andrey-core compute a correlation matrix once.
pgmpy and bnlearn compute it in every call.
The total includes this setup, so it is a fair view of both styles.

A mark on a cell means that the package computes a different test or uses a different rule.
Read the notes under the table before you compare such a cell.

The agreement table lists the largest absolute difference in p-value between a package and FastCIT.
A value near 1e-10 or smaller means the two packages compute the same statistic.
A larger value comes from a known difference in the definition.
Each such row has a note.

Known differences:

- andrey-core uses a different degrees-of-freedom rule for χ² and G².
- bnlearn uses the nominal degrees of freedom by default.
  The `adf` rows use the adjusted degrees of freedom.
- pcalg `disCItest` with `adaptDF = FALSE` uses the nominal degrees of freedom.
- pgmpy `PillaiTrace` uses a random forest.
- causal-learn, andrey-core and dHSIC use a different kernel width or null approximation for HSIC.
  causal-learn uses a different one for KCI.
- andrey-core KCI can swap X and Y.
  The table compares it with FastCIT with X and Y swapped when this gives a closer match.

Times depend on the machine.
Compare the cells in one row of one table.
Do not compare numbers from different runs.
