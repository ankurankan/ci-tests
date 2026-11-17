# Time FastCIT (R) against pcalg, bnlearn, dHSIC, Rfast, ppcor and comets on the shared queries.
#
# Usage: Rscript benchmarks/bench_r.R OUTDIR [--quick] [--seed N] [--out FILE]
#
# OUTDIR must hold the files written by benchmarks/data.py. The script writes OUTDIR/FILE (default r.json).
# Run the script three times, each in a new process, with --seed 1, 2 and 3 and --out r-1.json, r-2.json
# and r-3.json. benchmarks/summarize.py merges the runs.
#
# Timing method: each row runs 5 passes. Each pass runs the engines of the row in a new random order
# (from --seed), so that a slow period of the machine spreads over the engines. Before each engine pass,
# the script runs gc(full = TRUE) outside the timer. Each engine pass builds new test objects (timed as
# setup) and then times every query once. The time of a query is the best of the 5 passes.
# The per-call result of a row is the median of those per-query times, in milliseconds.
# A query that raises an error or returns NaN is counted and left out of the median.
# The second result is the total per pass: setup (build the per-dataset state) plus all queries
# of the group, once. The script reports the best of the 5 passes.
# The script also times a no-op engine through the same code (the harness floor) and records its median.
# It does not subtract the floor from any result.

suppressPackageStartupMessages({
  library(fastcit); library(pcalg); library(bnlearn); library(dHSIC); library(jsonlite)
})
# Rfast, ppcor and comets are called with `::`. Attaching them would mask base functions.
for (p in c("Rfast", "ppcor", "comets")) if (!requireNamespace(p, quietly = TRUE)) stop("package ", p, " is not installed")

args <- commandArgs(trailingOnly = TRUE)
quick <- "--quick" %in% args
args <- setdiff(args, "--quick")
option <- function(name, default) {
  i <- match(name, args)
  if (is.na(i)) return(default)
  if (i == length(args)) stop("missing value for ", name)
  value <- args[i + 1]
  args <<- args[-c(i, i + 1)]
  value
}
out_name <- option("--out", "r.json")
seed <- as.integer(option("--seed", "1"))
if (length(args) != 1) stop("Usage: Rscript benchmarks/bench_r.R OUTDIR [--quick] [--seed N] [--out FILE]")
outdir <- args[1]
PASSES <- 5L
Q <- fromJSON(file.path(outdir, "queries.json"), simplifyVector = FALSE)
read_data <- function(group) read.csv(file.path(outdir, Q[[group]]$data), check.names = FALSE)

script_dir <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(), value = TRUE)[1]))
source(file.path(script_dir, "r_engines.R"))  # engines, timing core, metadata helpers

# Run PASSES passes over the engines of one row. The passes are the outer loop. orders[[pass]] gives the
# engine order of each pass, so that a slow period of the machine does not hit one engine only.
time_row <- function(engines, qs, orders) {
  states <- lapply(engines, function(e) new_state(length(qs)))
  for (pass in seq_len(PASSES)) {
    for (eng in orders[[pass]]) states[[eng]] <- time_pass(engines[[eng]], qs, states[[eng]], pass == 1L)
  }
  lapply(states, result)
}

d <- read_data("discrete"); g <- read_data("gaussian"); h <- read_data("hsic")
ROWS <- bench_rows(d, g, h)

meta <- list(
  date = format(Sys.time(), "%Y-%m-%d %H:%M:%S"), cpu = cpu_name(), logical_cpus = parallel::detectCores(),
  os = paste(Sys.info()[["sysname"]], Sys.info()[["release"]]), r = R.version.string, quick = quick,
  passes = PASSES, seed = seed, uptime_start = sh("uptime"), power = power_state(),
  affinity = list(cpus_allowed_list = cpu_affinity()),
  versions = list(fastcit = as.character(packageVersion("fastcit")), pcalg = as.character(packageVersion("pcalg")),
                  bnlearn = as.character(packageVersion("bnlearn")), dHSIC = as.character(packageVersion("dHSIC")),
                  Rfast = as.character(packageVersion("Rfast")), ppcor = as.character(packageVersion("ppcor")),
                  comets = as.character(packageVersion("comets"))),
  commits = list(fastcit = fastcit_commit(script_dir)), fastcit_trees = fastcit_trees(script_dir),
  threads = list(env = as.list(env_threads), fastcit = "single-threaded (no rayon)",
                 blas = unname(extSoftVersion()[["BLAS"]]), lapack = La_library())
)
# The engine order of every pass of every row, drawn before any engine runs.
set.seed(seed)
orders <- lapply(ROWS, function(spec) lapply(seq_len(PASSES), function(p) sample(names(spec$engines))))
# The harness floor: a no-op engine on the discrete queries, through the same timing code.
floor_qs <- Q$discrete$queries
if (quick) floor_qs <- floor_qs[seq_len(min(2, length(floor_qs)))]
harness <- time_row(list(noop = noop), floor_qs, rep(list("noop"), PASSES))$noop
meta$harness_floor_ms <- harness$median_ms
cat(sprintf("harness floor: median %.6f ms\n", harness$median_ms))
results <- list()
for (row in names(ROWS)) {
  spec <- ROWS[[row]]
  qs <- Q[[spec$group]]$queries
  if (quick) qs <- qs[seq_len(min(2, length(qs)))]
  results[[row]] <- list(label = spec$label, engines = time_row(spec$engines, qs, orders[[row]]))
  for (eng in names(spec$engines)) {
    res <- results[[row]]$engines[[eng]]
    cat(sprintf("%-10s %-16s median %.4f ms, total %.2f ms (%d q, %d errors, %d NaN)\n", row, eng, res$median_ms, res$total_ms, length(qs), res$errors, res$nan))
  }
}
meta$uptime_end <- sh("uptime")
meta$power_end <- power_state()
writeLines(toJSON(list(meta = meta, results = results), auto_unbox = TRUE, digits = NA, na = "null", pretty = TRUE),
           file.path(outdir, out_name))
