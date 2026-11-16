# Time FastCIT (R) against pcalg, bnlearn and dHSIC on the shared queries.
#
# Usage: Rscript benchmarks/bench_r.R OUTDIR [--quick]
#
# OUTDIR must hold the files written by benchmarks/data.py. The script writes OUTDIR/r.json.
#
# Timing method: each engine runs 3 passes. Each pass builds new test objects (not timed).
# Each pass times every query once. The time of a query is the best of the 3 passes.
# The per-call result of a row is the median of those per-query times, in milliseconds.
# A query that raises an error or returns NaN is counted and left out of the median.
# The second result is the total per pass: setup (build the per-dataset state) plus all queries
# of the group, once. The script reports the best of the 3 passes.

suppressPackageStartupMessages({
  library(fastcit); library(pcalg); library(bnlearn); library(dHSIC); library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
quick <- "--quick" %in% args
args <- setdiff(args, "--quick")
if (length(args) != 1) stop("Usage: Rscript benchmarks/bench_r.R OUTDIR [--quick]")
outdir <- args[1]
PASSES <- 3L
Q <- fromJSON(file.path(outdir, "queries.json"), simplifyVector = FALSE)
read_data <- function(group) read.csv(file.path(outdir, Q[[group]]$data), check.names = FALSE)

# An engine factory builds the test objects outside the timer.
# It returns run(x, y, z) -> list(stat, p). run() runs inside the timer.
# bnlearn ci.test() checks the whole data frame in each call. The query gets only its own columns.
# The subset is built before the timer starts, so the timer covers only the ci.test() call.
bn_subset <- function(data, test) {
  list(prepare = function(x, y, z) data[, unique(c(x, y, z)), drop = FALSE],
       run = function(sub, x, y, z) {
         r <- if (length(z)) bnlearn::ci.test(x, y, z, data = sub, test = test)
              else bnlearn::ci.test(x, y, data = sub, test = test)
         list(stat = unname(r$statistic), p = unname(r$p.value))
       })
}
fc <- function(ctor, df) {
  function() {
    t <- ctor(fastcit::dataset(df))
    function(x, y, z) { r <- fastcit::run_test(t, x, y, z); list(stat = r$statistic, p = r$p_value) }
  }
}

time_engine <- function(factory, qs) {
  n <- length(qs)
  best <- rep(Inf, n); ps <- rep(NA_real_, n); st <- rep(NA_real_, n)
  err <- rep(FALSE, n); nan <- rep(FALSE, n); totals <- numeric(0); setups <- numeric(0)
  for (pass in seq_len(PASSES)) {
    t0 <- Sys.time()
    run <- factory()  # new objects each pass, so no state carries over
    setup <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
    total <- setup
    for (i in seq_along(qs)) {
      q <- qs[[i]]; z <- as.character(unlist(q$z))
      arg <- if (is.list(run)) run$prepare(q$x, q$y, z) else NULL  # not timed
      t0 <- Sys.time()
      r <- tryCatch(if (is.list(run)) run$run(arg, q$x, q$y, z) else run(q$x, q$y, z), error = function(e) {
        if (!err[i]) message("  error: ", conditionMessage(e))
        NULL
      })
      dt <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
      total <- total + dt
      best[i] <- min(best[i], dt)
      if (is.null(r)) err[i] <- TRUE
      else if (!is.finite(r$p)) nan[i] <- TRUE
      if (pass == 1L && !is.null(r)) {
        ps[i] <- if (is.finite(r$p)) r$p else NA_real_
        if (!is.null(r$stat) && is.finite(r$stat)) st[i] <- r$stat
      }
    }
    totals <- c(totals, total); setups <- c(setups, setup)
  }
  ok <- !err & !nan
  list(median_ms = if (any(ok)) 1e3 * median(best[ok]) else NA, total_ms = 1e3 * min(totals), setup_ms = 1e3 * min(setups),
       n_queries = n, n_timed = sum(ok), errors = sum(err), nan = sum(nan), ms = 1e3 * best, p = ps, stat = st)
}

d <- read_data("discrete"); dfac <- as.data.frame(lapply(d, factor)); dint <- as.data.frame(lapply(d, as.integer))
ix <- setNames(seq_along(d), names(d)); nlev <- sapply(d, function(c) length(unique(c)))
pc_disc <- function(adapt) function() {
  ss <- list(dm = as.matrix(d), nlev = nlev, adaptDF = adapt)
  function(x, y, z) list(p = pcalg::disCItest(ix[[x]], ix[[y]], unname(ix[z]), ss))
}
g <- read_data("gaussian"); gi <- setNames(seq_along(g), names(g))
h <- read_data("hsic")

ROWS <- list(
  chi_square = list(group = "discrete", label = "chi-squared", engines = list(
    fastcit = fc(function(ds) fastcit::chi_squared(ds, yates = FALSE), dint),
    bnlearn = function() bn_subset(dfac, "x2"),
    `bnlearn (adf)` = function() bn_subset(dfac, "x2-adf"))),
  g_sq = list(group = "discrete", label = "G-squared", engines = list(
    fastcit = fc(function(ds) fastcit::log_likelihood(ds, yates = FALSE), dint),
    pcalg = pc_disc(FALSE),
    `pcalg (adaptDF)` = pc_disc(TRUE),
    bnlearn = function() bn_subset(dfac, "mi"),
    `bnlearn (adf)` = function() bn_subset(dfac, "mi-adf"))),
  fisher_z = list(group = "gaussian", label = "Fisher-z", engines = list(
    fastcit = fc(fastcit::fisher_z, g),
    pcalg = function() {
      ss <- list(C = cor(g), n = nrow(g))  # the correlation matrix is built once, outside the timer
      function(x, y, z) list(p = pcalg::gaussCItest(gi[[x]], gi[[y]], unname(gi[z]), ss))
    },
    bnlearn = function() bn_subset(g, "zf"))),
  pearson_t = list(group = "gaussian", label = "Pearson t", engines = list(
    fastcit = fc(fastcit::pearson_correlation, g),
    bnlearn = function() bn_subset(g, "cor"))),
  hsic = list(group = "hsic", label = "HSIC (median width)", engines = list(
    fastcit = fc(function(ds) fastcit::hsic(ds, bandwidth = "median"), h),
    dHSIC = function() function(x, y, z) {
      r <- dHSIC::dhsic.test(h[[x]], h[[y]], method = "gamma", kernel = "gaussian")
      list(stat = r$statistic, p = r$p.value)
    }))
)

script_dir <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(), value = TRUE)[1]))
sh <- function(cmd) tryCatch(paste(system(cmd, intern = TRUE), collapse = " "), error = function(e) "")
cpu <- trimws(sh("grep -m1 'model name' /proc/cpuinfo | cut -d: -f2"))
if (!nzchar(cpu)) cpu <- trimws(sh("sysctl -n machdep.cpu.brand_string"))
if (!nzchar(cpu)) cpu <- paste("unknown", Sys.info()[["machine"]])
fastcit_commit <- function() {
  env <- Sys.getenv("FASTCIT_COMMIT", "")
  if (nzchar(env)) return(env)
  head <- sh(paste("git -C", shQuote(script_dir), "rev-parse --short HEAD"))
  if (!nzchar(head)) return("unknown")
  dirty <- sh(paste("git -C", shQuote(script_dir), "status --porcelain"))
  paste0(head, if (nzchar(dirty)) "-dirty" else "")
}
env_threads <- Filter(nzchar, Sys.getenv(c("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")))
affinity <- tryCatch({
  l <- readLines("/proc/self/status"); trimws(sub("^Cpus_allowed_list:", "", grep("^Cpus_allowed_list", l, value = TRUE)))
}, error = function(e) "")
meta <- list(
  date = format(Sys.time(), "%Y-%m-%d %H:%M:%S"), cpu = cpu, logical_cpus = parallel::detectCores(),
  os = paste(Sys.info()[["sysname"]], Sys.info()[["release"]]), r = R.version.string, quick = quick,
  passes = PASSES, uptime_start = sh("uptime"), affinity = list(cpus_allowed_list = affinity),
  versions = list(fastcit = as.character(packageVersion("fastcit")), pcalg = as.character(packageVersion("pcalg")),
                  bnlearn = as.character(packageVersion("bnlearn")), dHSIC = as.character(packageVersion("dHSIC"))),
  commits = list(fastcit = fastcit_commit()),
  threads = list(env = as.list(env_threads), fastcit = "single-threaded (no rayon)",
                 blas = unname(extSoftVersion()[["BLAS"]]), lapack = La_library())
)
results <- list()
for (row in names(ROWS)) {
  spec <- ROWS[[row]]
  qs <- Q[[spec$group]]$queries
  if (quick) qs <- qs[seq_len(min(2, length(qs)))]
  results[[row]] <- list(label = spec$label, engines = list())
  for (eng in names(spec$engines)) {
    res <- time_engine(spec$engines[[eng]], qs)
    results[[row]]$engines[[eng]] <- res
    cat(sprintf("%-10s %-16s median %.4f ms, total %.2f ms (%d q, %d errors, %d NaN)\n", row, eng, res$median_ms, res$total_ms, length(qs), res$errors, res$nan))
  }
}
meta$uptime_end <- sh("uptime")
writeLines(toJSON(list(meta = meta, results = results), auto_unbox = TRUE, digits = NA, na = "null", pretty = TRUE),
           file.path(outdir, "r.json"))
