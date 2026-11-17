# Time FastCIT (R) and the R packages of bench_r.R at a grid of sample sizes n and of conditioning-set sizes |Z|.
#
# Usage: Rscript benchmarks/sweep_r.R OUTDIR [--quick] [--rows a,b,...] [--sweep n|z] [--seed N] [--out FILE]
#
# OUTDIR must hold the files written by benchmarks/sweep_data.py. The script writes OUTDIR/FILE (default
# sweep-r.json). The run file has the shape documented in benchmarks/sweep_python.py: the same row and sweep keys,
# the same grids (read from sweep-queries.json), and the same POINT fields. The engine of FastCIT is "fastcit". The engines come from r_engines.R.
# --quick runs the two smallest points of each sweep with 2 queries and 1 pass.
#
# Rows: the rows of bench_r.R (the "bnlearn (adf)" and "pcalg (adaptDF)" variants exist there for the agreement
# check only and are not timed here), and FastCIT-only rows for the tests with no R package: cressie_read,
# freeman_tukey, modified_ll, pearson_equivalence, kci and pillai.
# Sweeps (the grids are the "plan" of sweep-queries.json, written by sweep_data.py):
#   n: n rows (the first n rows of the data file) at |Z| = 1 (HSIC: Z empty).
#   z: |Z| = 0..4 at a fixed n (10 000; pillai 2 000; kci 500). HSIC has no |Z| sweep.
# Every query of a point has exactly |Z| conditioning variables. 20 queries per point (kernel rows: 10).
#
# Timing: 3 passes per point. The passes are the outer loop. Each pass runs the engines of the point in a new random
# order (seeded). gc(full = TRUE) runs before each engine pass, outside the timer. Each engine pass builds new test
# objects and times every query once. The time of a query is its best pass. The value of a point is the median over
# the queries, in milliseconds. A query that raises an error or returns NaN is counted and left out.
# Time budget: when the first pass of an engine at a point takes more than 60 s, the engine skips the remaining
# passes of that point (the value comes from one pass) and all larger points of that sweep. Those points get
# "median_ms": null and "skipped": "time budget".

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
out_name <- option("--out", "sweep-r.json")
seed <- as.integer(option("--seed", "1"))
only_sweep <- option("--sweep", "")
only_rows <- option("--rows", "")
usage <- "Usage: Rscript benchmarks/sweep_r.R OUTDIR [--quick] [--rows a,b,...] [--sweep n|z] [--seed N] [--out FILE]"
if (length(args) != 1) stop(usage)
if (!only_sweep %in% c("", "n", "z")) stop("--sweep must be n or z")
outdir <- args[1]
PASSES <- if (quick) 1L else 3L
BUDGET_S <- as.numeric(Sys.getenv("FASTCIT_SWEEP_BUDGET_S", "60"))  # the variable lets a test trip the budget
script_dir <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(), value = TRUE)[1]))
source(file.path(script_dir, "r_engines.R"))  # engines, timing core, metadata helpers
spec <- fromJSON(file.path(outdir, "sweep-queries.json"), simplifyVector = FALSE)

if (is.null(spec$plan)) stop("sweep-queries.json has no plan; run sweep_data.py again")
# The plan (grids, and per row the generator, n grid, n_z and z_n) comes from sweep-queries.json, written by
# sweep_data.py. z_n is null for a row without |Z| sweep (HSIC).
grids <- lapply(spec$plan$grids, unlist)
Z_GRID <- grids$z
PLAN <- lapply(spec$plan$rows, function(r) list(gen = r$gen, n_grid = unlist(r$n_grid), n_z = r$n_z, z_n = r$z_n))

# The engines of each row on the first n rows of the data of its generator. `data` is that frame.
UNTIMED <- c("bnlearn (adf)", "pcalg (adaptDF)")  # agreement-check variants of bench_r.R
drop_untimed <- function(rows) lapply(rows, function(r) { r$engines <- r$engines[!names(r$engines) %in% UNTIMED]; r })
only <- function(label, factory) list(label = label, engines = list(fastcit = factory))
engines_for <- function(gen, data) {
  switch(gen,
    discrete = {
      dint <- as.data.frame(lapply(data, as.integer))
      c(drop_untimed(discrete_rows(data)), list(
        cressie_read = only("Cressie-Read", fc(function(ds) fastcit::cressie_read(ds, yates = FALSE), dint)),
        freeman_tukey = only("Freeman-Tukey", fc(function(ds) fastcit::freeman_tukey(ds, yates = FALSE), dint)),
        modified_ll = only("Modified log-likelihood",
                           fc(function(ds) fastcit::modified_likelihood(ds, yates = FALSE), dint))))
    },
    gaussian = c(drop_untimed(gaussian_rows(data)), list(
      pearson_equivalence = only("Pearson equivalence", fc(fastcit::pearson_equivalence, data)))),
    mixed = list(pillai = only("Pillai", fc(fastcit::pillai, data))),
    nonlinear = c(hsic_rows(data), list(kci = only("KCI", fc(fastcit::kci, data)))))
}

read_frame <- function(gspec) {
  df <- read.csv(file.path(outdir, gspec$data), check.names = FALSE, stringsAsFactors = FALSE)
  for (c in names(df)) if (is.character(df[[c]])) df[[c]] <- factor(df[[c]])  # the categorical columns of "mixed"
  df
}
# The first n rows. Discrete codes are recoded to 0..k-1 (Rfast and pcalg need contiguous codes), as
# the Python harness drops unused categories.
head_frame <- function(df, gen, n) {
  part <- df[seq_len(n), , drop = FALSE]
  rownames(part) <- NULL
  for (c in names(part)) {
    if (is.factor(part[[c]])) part[[c]] <- droplevels(part[[c]])
    else if (gen == "discrete") part[[c]] <- match(part[[c]], sort(unique(part[[c]]))) - 1L
  }
  part
}

point_result <- function(median_ms = NA_real_, ms = NA, errors = 0L, nan = 0L, n_queries = 0L, n_timed = 0L,
                         passes = 0L, skipped = NA_character_, error = NA_character_, setup_ms = NA_real_, total_ms = NA_real_) {
  list(median_ms = median_ms, ms = if (identical(ms, NA)) NA else I(ms), errors = errors, nan = nan,
       n_queries = n_queries, n_timed = n_timed, passes = passes, skipped = skipped, error = error,
       setup_ms = setup_ms, total_ms = total_ms)
}
skipped_point <- function(n_queries) point_result(n_queries = n_queries, skipped = "time budget")

# A seed from a text key, so that the engine orders do not depend on the run order of the rows.
key_seed <- function(key) as.integer(sum(utf8ToInt(key) * seq_len(nchar(key))) %% 2147483647)

# Run the passes over the engines at one point. Returns the point of each engine and the engines over the budget.
time_point <- function(engines, qs, key) {
  states <- lapply(engines, function(e) new_state(length(qs)))
  failed <- list(); over <- character(0)
  active <- names(engines)
  set.seed(key_seed(key))
  for (pass in seq_len(PASSES)) {
    for (name in sample(active)) {
      st <- tryCatch(time_pass(engines[[name]], qs, states[[name]], pass == 1L), error = function(e) {
        failed[[name]] <<- substr(paste0("error: ", conditionMessage(e)), 1, 100)  # the factory failed
        NULL
      })
      if (is.null(st)) { active <- setdiff(active, name); next }
      states[[name]] <- st
      if (pass == 1L && st$totals[1] > BUDGET_S) { over <- c(over, name); active <- setdiff(active, name) }
    }
  }
  out <- lapply(names(engines), function(name) {
    if (!is.null(failed[[name]])) return(point_result(error = failed[[name]], errors = length(qs), n_queries = length(qs)))
    st <- states[[name]]; res <- result(st); ok <- !st$err & !st$nan
    point_result(median_ms = res$median_ms, ms = ifelse(ok, res$ms, NA_real_), errors = res$errors, nan = res$nan,
                 n_queries = res$n_queries, n_timed = res$n_timed, passes = length(st$totals),
                 setup_ms = res$setup_ms, total_ms = res$total_ms)
  })
  list(points = setNames(out, names(engines)), over = over)
}

meta <- list(
  kind = "sweep", date = format(Sys.time(), "%Y-%m-%d %H:%M:%S"), cpu = cpu_name(), logical_cpus = parallel::detectCores(),
  os = paste(Sys.info()[["sysname"]], Sys.info()[["release"]]), r = R.version.string, quick = quick,
  passes = PASSES, time_budget_s = BUDGET_S, seed = seed,
  grids = lapply(grids, I),
  uptime_start = sh("uptime"), power = power_state(), affinity = list(cpus_allowed_list = cpu_affinity()),
  versions = list(fastcit = as.character(packageVersion("fastcit")), pcalg = as.character(packageVersion("pcalg")),
                  bnlearn = as.character(packageVersion("bnlearn")), dHSIC = as.character(packageVersion("dHSIC")),
                  Rfast = as.character(packageVersion("Rfast")), ppcor = as.character(packageVersion("ppcor")),
                  comets = as.character(packageVersion("comets"))),
  commits = list(fastcit = fastcit_commit(script_dir)), fastcit_trees = fastcit_trees(script_dir),
  threads = list(env = as.list(env_threads), fastcit = "single-threaded (no rayon)",
                 blas = unname(extSoftVersion()[["BLAS"]]), lapack = La_library())
)
nq <- if (quick) 2L else Inf
take <- function(qs) qs[seq_len(min(nq, length(qs)))]
rows_wanted <- if (nzchar(only_rows)) strsplit(only_rows, ",")[[1]] else names(PLAN)
if (length(bad <- setdiff(rows_wanted, names(PLAN)))) stop("unknown rows: ", paste(bad, collapse = ", "))
if (nzchar(only_rows)) meta$rows <- I(rows_wanted)
sweeps <- if (nzchar(only_sweep)) only_sweep else c("n", "z")

# The harness floor: a no-op engine on the discrete queries of |Z| = 1, through the same timing code.
floor_pt <- time_point(list(noop = noop), take(spec$discrete$queries[["1"]]), paste(seed, "floor", sep = ":"))$points$noop
meta$harness_floor_ms <- floor_pt$median_ms
cat(sprintf("harness floor: median %.6f ms\n", floor_pt$median_ms))
results <- list()
path <- file.path(outdir, out_name)
save <- function(done = FALSE) {
  if (done) { meta$uptime_end <- sh("uptime"); meta$power_end <- power_state() }
  meta$engines <- I(unique(unlist(lapply(results, function(r) unlist(lapply(r$sweeps, function(s) names(s$engines)))))))
  writeLines(toJSON(list(meta = meta, results = results), auto_unbox = TRUE, digits = NA, na = "null", pretty = TRUE), path)
}

frame <- NULL; frame_gen <- ""  # one data file at a time
for (row in rows_wanted) {
  pl <- PLAN[[row]]; gspec <- spec[[pl$gen]]
  if (frame_gen != pl$gen) { frame <- read_frame(gspec); frame_gen <- pl$gen }
  results[[row]] <- list(label = NA_character_, sweeps = list())
  for (which in sweeps) {
    if (which == "z" && is.null(pl$z_n)) next
    if (which == "n") { xs <- pl$n_grid; ns <- xs; ks <- rep(pl$n_z, length(xs)); fixed <- list(z = pl$n_z) }
    else { xs <- Z_GRID; ns <- rep(pl$z_n, length(xs)); ks <- xs; fixed <- list(n = pl$z_n) }
    keep <- seq_len(if (quick) 2L else length(xs))
    keep <- keep[ns[keep] <= gspec$rows]  # a data file capped by --max-n has fewer rows
    xs <- xs[keep]; ns <- ns[keep]; ks <- ks[keep]
    series <- NULL; dead <- character(0)
    for (i in seq_along(xs)) {
      data <- head_frame(frame, pl$gen, ns[i])
      spec_row <- engines_for(pl$gen, data)[[row]]
      results[[row]]$label <- spec_row$label
      engines <- spec_row$engines
      if (is.null(series)) series <- setNames(lapply(names(engines), function(e) list()), names(engines))
      qs <- take(gspec$queries[[as.character(ks[i])]])
      if (!all(vapply(qs, function(q) length(q$z) == ks[i], logical(1))))
        stop(sprintf("%s %s x=%s: a query does not have %d conditioning variables", row, which, xs[i], ks[i]))
      live <- engines[!names(engines) %in% dead]
      res <- if (length(live)) time_point(live, qs, paste(seed, row, which, xs[i], sep = ":")) else list(points = list(), over = character(0))
      dead <- c(dead, res$over)
      for (e in names(engines)) {
        p <- res$points[[e]]
        if (is.null(p)) p <- skipped_point(length(qs))
        if (row == "g_sq" && e == "pcalg") p$note <- "pcalg returns p = 1 without running the test when n < 10 x the degrees of freedom. This happens at small n and at large |Z|, so these times are not comparable."
        series[[e]][[i]] <- p
        cat(sprintf("%-19s %s x=%-7d %-16s %s (%d q, %d errors, %d NaN)%s\n", row, which, xs[i], e,
                    if (!is.na(p$skipped)) paste0("skipped (", p$skipped, ")") else sprintf("median %s ms", format(p$median_ms)),
                    p$n_queries, p$errors, p$nan, if (!is.na(p$error)) paste0(" [", p$error, "]") else ""))
      }
    }
    results[[row]]$sweeps[[which]] <- list(fixed = fixed, x = I(as.integer(xs)), engines = series)
    save()
  }
}
save(done = TRUE)
