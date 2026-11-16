# FastCIT benchmarks

This folder holds a reproducible benchmark for FastCIT.
It compares the time of one test call in FastCIT with other packages.
It also records how closely the p-values agree.

## What the benchmark measures

The benchmark measures the time of one conditional independence test call.
It does not measure a full causal discovery run.

The scripts use the same data and the same queries for every package.
A query is one triple: variable X, variable Y, and a set of conditioning variables Z.

The benchmark runs three times for each language.
Each run is a new process.

Each run times every test in five passes.
In each pass, the packages of the test run in a new random order.
A seed sets the order, so a second run with the same seed uses the same order.
The random order spreads a slow period of the machine over the packages.
Before each package pass, the script runs the garbage collector, outside the timer.
Each pass builds new test objects.
The build time is not part of the result.
Caches are off when the package has an option for it.
Each pass times every query once.
The time of a query is the best of the five passes.
The run value of a test is the median of the query times, in milliseconds.

The tables show the median of the three run values.
The summary also gives the smallest and the largest run value of each cell.
The mark † shows a cell whose run values differ by more than 25 % of the cell value.

The scripts do not time a batch of repeated calls of one query.
FastCIT keeps a cache in the test object, so a repeated query is faster than a first query.

The scripts also time a no-op package through the same timing code.
This time is the harness floor.
The summary records the floor of each run.
The scripts do not subtract it from the results.

There are five discrete tests: χ², G², Cressie-Read, Freeman-Tukey and modified log-likelihood.
They run without the Yates correction in every package except pgmpy and gcastle.
pgmpy and gcastle cannot turn the correction off.
The agreement table compares both packages with FastCIT with the correction on.

### Python packages

| Test | FastCIT | pgmpy dev | causal-learn | gcastle | tigramite | pingouin | hyppo | dowhy |
|---|---|---|---|---|---|---|---|---|
| χ² | `ChiSquared` | `ChiSquare` | `chisq` | `chi2_test` | none | none | none | none |
| G² | `LogLikelihood` | `GSq` | `gsq` | `g2_test` | `Gsquared` | none | none | none |
| Cressie-Read | `CressieRead` | `PowerDivergence` | none | `cressie_read` | none | none | none | none |
| Freeman-Tukey | `FreemanTukey` | `PowerDivergence` | none | `freeman_tukey` | none | none | none | none |
| Modified log-likelihood | `ModifiedLikelihood` | `ModifiedLogLikelihood` | none | `modify_log_likelihood` | none | none | none | none |
| Fisher-z | `FisherZ` | `FisherZ` | `fisherz` | `fisherz_test` | none | none | none | none |
| Pearson t | `PearsonCorrelation` | `Pearsonr` | none | none | `ParCorr` | `partial_corr` | none | none |
| HSIC (n = 300) | `HSIC` | `HSIC` | `kci`, empty Z | none | none | none | `Hsic` | none |
| KCI (n = 300, 1 000) | `KCI` | `KCI` | `kci` | none | none | none | none | none |
| GCM | `GCM` | `GCM` | none | none | none | none | none | `generalised_cov_based` |
| Pillai | `PillaiTrace` | `PillaiTrace` | none | none | none | none | none | none |

The calls in detail:

- gcastle: `castle.common.independence_tests.CITest.<name>(data, x, y, z)`.
- tigramite: `ParCorr(significance="analytic")` and `Gsquared(significance="analytic")`.
  The script calls `set_dataframe` once per pass, and counts it as setup.
  Each query calls `run_test(X=[(i, 0)], Y=[(j, 0)], Z=[(k, 0), ...], tau_max=0)`.
- pingouin: `pingouin.partial_corr(data=df, x=x, y=y, covar=z)`.
  Each call goes through pandas, and this cost shows in the time.
- hyppo: `hyppo.independence.Hsic().test(x, y)` with the default settings.
  The p-value comes from a chi-squared approximation of the null.
- dowhy: `dowhy.gcm.independence_test.generalised_cov_based(x, y, z, prediction_model_X=create_linear_regressor, prediction_model_Y=create_linear_regressor)`.
  The default regression of dowhy picks a model by search, so it is a different test.
- pgmpy `PowerDivergence` runs with `lambda_="cressie-read"` for Cressie-Read and `lambda_=-0.5` for Freeman-Tukey.
  The pgmpy dev alias for Freeman-Tukey has a typo (`freeman-tuckey`), so the script passes the number.
- FastCIT and pgmpy run HSIC with `bandwidth="median"`, as the R row does.

dowhy does not support Python 3.14.
The benchmark runs it in a second interpreter, Python 3.11, and summarize.py merges the two result files.

The pgmpy `PillaiTrace` uses a random forest by default.
FastCIT uses a linear model.
The two tests are different, and the table marks this.

What the setup holds in each engine (not timed):

- FastCIT: the `Dataset` built from the data frame, and the test object.
  The correlation matrix is not part of it. FastCIT computes it in the first call.
- pgmpy: the test object, built from the data frame with the cache off.
- causal-learn: the `CIT` object, built from the data array.
- gcastle: the data array and the map from column names to indices.
- tigramite: the data frame and the `set_dataframe` call.
- pingouin: the data frame only.
- hyppo: one array for each column, and the `Hsic` object.
- dowhy: one array for each column.

The dowhy run also times FastCIT GCM in the same interpreter.
This time is a reference.
The summary prints it with the details of the run, not as a table column.

### R packages

| Test | FastCIT | pcalg | bnlearn | dHSIC | Rfast | ppcor | comets |
|---|---|---|---|---|---|---|---|
| χ² | `chi_squared` | none | `x2` | none | `chi2Test` | none | none |
| G² | `log_likelihood` | `disCItest` | `mi` | none | `g2Test` | none | none |
| Fisher-z | `fisher_z` | `gaussCItest` | `zf` | none | none | none | none |
| Pearson t | `pearson_correlation` | none | `cor` | none | none | `pcor.test` | none |
| HSIC (median width) | `hsic` | none | none | `dhsic.test` | none | none | none |
| GCM | `gcm` | none | none | none | none | none | `gcm` |

What the setup holds in each engine (not timed):

- FastCIT: the dataset and the test object.
- pcalg: the data matrix and the number of levels for the discrete tests.
  For Fisher-z it also holds the correlation matrix.
- Rfast: the data matrix of 0-based codes and the number of levels of each column, both stored as double.
- bnlearn, dHSIC, ppcor, comets: nothing.
  For bnlearn, ppcor and comets, the script cuts the columns of each query before the timer starts.

The pcalg G² test runs with `adaptDF = FALSE`.
The pcalg Fisher-z test gets a correlation matrix.
The script builds this matrix once, outside the timer.

Rfast needs 0-based codes and the number of levels of each column.
Store the codes and the numbers of levels as double.
The C++ code of Rfast takes double values.
With an integer matrix, Rfast copies the whole matrix to double in every call.
The script converts the matrix once, in the setup.
`chi2Test` and `g2Test` return the statistic and the degrees of freedom.
The script computes the p-value with `pchisq` inside the timer.
Rfast crashes R when the codes start at 1.

The ppcor function `pcor.test` needs at least one conditioning variable.
For a query with an empty Z, the script calls `stats::cor.test`.
This is the same t-test.
9 of the 50 Gaussian queries have an empty Z.

comets runs `gcm(Y, X, Z, reg_YonZ = "lrm", reg_XonZ = "lrm", type = "scalar")`.
The default regression of comets is a random forest, which is a different test.

## Data

`data.py` writes all data.
The data are synthetic.
The script fixes the seeds.
The script downloads nothing.

| Data | Shape | Used by |
|---|---|---|
| Discrete | 30 variables with 2 to 4 levels, n = 10 000, random DAG with random tables | χ², G², Cressie-Read, Freeman-Tukey, modified log-likelihood |
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

Use Python 3.11 to 3.14.
Use a recent R.
Install the Python packages with pinned versions.
The run in `results` used these versions of numpy, pandas, scipy and scikit-learn.
The dowhy run used its own numeric stack: numpy 2.4.6, pandas 3.1.1, scipy 1.15.3 and scikit-learn 1.9.1.

```bash
pip install causal-learn==0.1.4.5 numpy==2.4.1 pandas==3.0.0 scipy==1.17.0 scikit-learn==1.8.0
pip install "pgmpy @ git+https://github.com/pgmpy/pgmpy.git@a67c17d9"
```

The smaller packages come without their dependencies.
The benchmark imports only the test modules of gcastle and tigramite.
These modules need no torch and no numba.
The other packages need the extra libraries in the second command.

```bash
pip install --no-deps gcastle==1.0.4 tigramite==5.2.10.1 pingouin==0.7.0 hyppo==0.5.2
pip install statsmodels==0.15.0 pandas-flavor==0.8.1 tabulate==0.10.0 xarray==2026.9.0 lazy_loader==0.6 \
  autograd==1.9.1 numba==0.68.1 llvmlite==0.50.0 patsy==1.0.3 future==1.0.0 threadpoolctl==3.6.0
```

dowhy needs Python 3.9 to 3.13.
Install it in a second environment with Python 3.11.
The environment has its own numpy, pandas, scipy and scikit-learn.
The command pins the versions of the run in `results`.
The environment also needs FastCIT for the reference time.
The script records the versions in `python-dowhy-1.json` and the other run files.

```bash
python3.11 -m venv dowhy-env
dowhy-env/bin/pip install dowhy==0.14 numpy==2.4.6 pandas==3.1.1 scipy==1.15.3 scikit-learn==1.9.1
dowhy-env/bin/pip install ./crates/ci-python
```

Build FastCIT from this repository.
Note the commit of the repository in your result.

```bash
pip install ./crates/ci-python
```

You can also build a wheel instead.
Run `maturin build --release -m crates/ci-python/Cargo.toml`.
Then install the wheel.

Install the R packages with pinned versions.
The pcalg package needs the Bioconductor packages `graph` and `RBGL`.

```r
install.packages(c("remotes", "BiocManager", "jsonlite"))
BiocManager::install(c("graph", "RBGL"))
remotes::install_version("bnlearn", "5.2.1")
remotes::install_version("dHSIC", "2.2")
remotes::install_version("pcalg", "2.7.12")
remotes::install_version("ppcor", "1.1")
remotes::install_version("comets", "0.2-3")
remotes::install_version("Rfast", "2.1.5.2")
```

Rfast compiles from source and needs `cmake`.
The compile takes more than an hour on a busy laptop, because the package has about 75 C++ files.
Start it before you need it.

Install the FastCIT R package from this repository.

The build writes the package file to the current folder.
Build in a temporary folder, so the repository stays clean.

```bash
REPO="$(pwd)"
cd "$(mktemp -d)"
R CMD build "$REPO/crates/ci-r"
R CMD INSTALL fastcit_*.tar.gz
cd "$REPO"
```

The scripts record the installed versions, the FastCIT commit, the thread settings and the CPU affinity.
The FastCIT commit is the commit of the checkout that holds the scripts.
It gets the suffix `-dirty` when the working tree has changes.
Set `FASTCIT_COMMIT` when the installed FastCIT comes from another commit.

The scripts also record the git tree hashes of the FastCIT code.
The hashes name `crates/ci-core` and `crates/ci-python` for Python, and `crates/ci-core` and `crates/ci-r` for R.
A squash merge removes the commit of the branch, but the tree hashes stay valid.
Check a hash in any checkout with `git rev-parse <commit>:crates/ci-core`.
The hash must equal the recorded value, for the commit that you compare.
The scripts read the pgmpy commit from the pip metadata.
If you use a source archive, set `PGMPY_COMMIT=a67c17d9` before you run `bench_python.py`.
Without this value, the scripts record `unknown`.

## Run

Pick an output folder.
Run these commands from the repository root.

```bash
python benchmarks/data.py OUT
for k in 1 2 3; do
  taskset -c 0-11 python benchmarks/bench_python.py OUT --seed $k --out python-$k.json
  taskset -c 0-11 dowhy-env/bin/python benchmarks/bench_python.py OUT --engines dowhy,fastcit --rows gcm \
    --seed $k --out python-dowhy-$k.json
  taskset -c 0-3 Rscript benchmarks/bench_r.R OUT --seed $k --out r-$k.json
done
python benchmarks/summarize.py OUT
```

Each command starts a new process, so each run is independent.
Wait for a low load before each command.

`bench_python.py` runs every engine whose package imports in the current interpreter.
Pick engines with `--engines a,b` and tests with `--rows a,b`.
Name the result file with `--out FILE`.
`--seed` sets the order of the packages in each pass.
`summarize.py` reads every file `NAME-k.json` in the folder.
The files with the same `NAME` are the runs of one group.
The `python` group comes from the main interpreter.
A group `python-NAME` comes from another interpreter, and its packages join the Python tables.
FastCIT in such a group is the reference time.

Add `--quick` to `bench_python.py` and `bench_r.R` for a short test run.
A quick run uses 2 queries per group.

One Python run takes about 3 minutes.
One dowhy run takes a few seconds.
One R run takes about 30 seconds.
Use a quiet machine.
Stop compile jobs before a run.
Wait until the load in `uptime` is below 1.5.
Check the load with `uptime` before and after each run.
The scripts record both values.
On a laptop, connect the charger. Set the power profile to `performance`.
The scripts record the power state at the start and at the end of each run.
The power state is the AC adapter, the power profile, and the governor and EPP of CPU 0.

The scripts use the default thread count of each package.
FastCIT runs on one thread.
The scripts record the BLAS libraries and their thread counts.

The runs in `results` used CPU pinning.
The test machine has two P-cores (CPUs 0 to 3) and eight E-cores (CPUs 4 to 11).
It also has two low-power E-cores (CPUs 12 and 13), which run at 2.1 GHz at most.
The R runs used `taskset -c 0-3`, so they ran on the P-cores.
The R packages and FastCIT run on one thread.
The Python runs used `taskset -c 0-11`, so they did not use the low-power E-cores.
This leaves 12 BLAS threads for the other Python packages.
In the R runs in `results`, the run values of a cell differ by at most 6 % of the cell value.
In the total tables of R, they differ by at most 14 %.
The Python run values of a cell differ by at most 12 % in both kinds of table.
The spread tables in `summary.md` give the range of each cell.

To publish a result, replace the run files in the results folder.

```bash
rm benchmarks/results/python-*.json benchmarks/results/r-*.json
cp OUT/python-*.json OUT/r-*.json benchmarks/results/
python benchmarks/summarize.py benchmarks/results
```

The `data.py` script writes CSV files.
Do not commit them.

## Results

The `results` folder holds the files of the last full run.

| File | Content |
|---|---|
| `results/python-1.json` to `python-3.json` | One run each: median time, total time, per-query times and p-values for each Python package in the main interpreter |
| `results/python-dowhy-1.json` to `python-dowhy-3.json` | The same data for dowhy and the FastCIT reference, under Python 3.11 |
| `results/r-1.json` to `r-3.json` | The same data for each R package |
| `results/summary.md` | Tables, spread across runs, run details and agreement |
| `results/summary.json` | The same tables as data, for the documentation home page |

`summary.md` starts with the run details.
They are the CPU, operating system, package versions, commit hashes and tree hashes.
For each run, they also give the date, power state, harness floor and load.

## How to read the tables

Each cell holds the median time of one test call, in milliseconds.
A lower number is better.
A dash means that the package has no test with this definition, or that the benchmark has no result.
A star means that the package raised an error or returned NaN on some queries.
The median uses only the queries with a result.
Those queries can cost less or more than the excluded ones.
Compare such a cell with care.
A dagger (†) means that the run values of the cell differ by more than 25 % of the cell value.
The spread tables in `summary.md` give the smallest and the largest run value.

The total-per-pass tables show a second metric.
A pass builds the state of the package and runs all queries of the group once.
FastCIT, pcalg and causal-learn compute a correlation matrix once.
The other packages compute it in every call.
The total includes this setup, so it is a fair view of both styles.
The total tables carry the same cell marks as the median tables.

A mark on a cell means that the package computes a different test or uses a different rule.
Read the notes under the table before you compare such a cell.

The agreement table lists the largest absolute difference in p-value between a package and FastCIT.
A value near 1e-10 or smaller means the two packages compute the same statistic.
A larger value comes from a known difference in the definition.
Each such row has a note.

Known differences:

- pgmpy and gcastle apply the Yates correction on 2 × 2 tables and cannot turn it off.
  They use it for χ², G², Cressie-Read, Freeman-Tukey and modified log-likelihood.
  gcastle calls `scipy.stats.chi2_contingency` with its default `correction=True`.
  The agreement table compares both packages with FastCIT with the correction on.
- On sparse tables, pgmpy and gcastle return NaN for Freeman-Tukey in 15 of 50 queries.
  pgmpy returns NaN for one G² query and one modified log-likelihood query.
  FastCIT returns a value for all of them.
  The tables mark these cells with a star, and the median leaves the queries out.
- bnlearn and Rfast use the nominal degrees of freedom.
  The bnlearn `adf` rows use the adjusted degrees of freedom.
- Rfast `chi2Test` returns NaN when a table has an empty row or column.
  This happens in 6 of 50 queries.
- pcalg `disCItest` with `adaptDF = FALSE` uses the nominal degrees of freedom.
- pgmpy `PillaiTrace` uses a random forest.
- causal-learn, hyppo and dHSIC use a different kernel width or null approximation for HSIC.
  hyppo uses a chi-squared approximation of the null.
  causal-learn uses a different one for KCI.
- pgmpy HSIC with `bandwidth="median"` matches FastCIT, so the table carries no mark for it.
- ppcor calls `stats::cor.test` for queries with an empty Z.
- bnlearn `ci.test()` checks the whole data frame in each call.
  The benchmark gives it only the columns of the query.
  This is closer to the cost inside bnlearn structure learning.
- gcastle builds a data frame and groups it in every call of the discrete tests.
- pingouin and tigramite compute the partial correlation from the data in every call.
  pingouin also goes through pandas in every call.
- dowhy `generalised_cov_based` needs the linear regressors for a test that matches FastCIT.
  Its default regression is a different test.
- comets with `reg_YonZ = "lrm"` and `reg_XonZ = "lrm"` matches FastCIT.

Times depend on the machine.
Compare the cells in one row of one table.
Do not compare numbers from different runs.
