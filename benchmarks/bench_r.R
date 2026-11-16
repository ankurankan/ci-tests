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
# ppcor::pcor.test() needs at least one conditioning variable. A query with an empty Z calls
# stats::cor.test(), which runs the same t-test on the correlation. The columns are cut before the timer starts.
ppcor_cols <- function(data) {
  list(prepare = function(x, y, z) list(x = data[[x]], y = data[[y]], z = as.matrix(data[, z, drop = FALSE])),
       run = function(a, x, y, z) {
         r <- if (length(z)) ppcor::pcor.test(a$x, a$y, a$z) else stats::cor.test(a$x, a$y)
         list(stat = unname(r$statistic), p = unname(r$p.value))
       })
}
comets_gcm <- function(data) {
  list(prepare = function(x, y, z) list(x = data[[x]], y = data[[y]], z = as.matrix(data[, z, drop = FALSE])),
       run = function(a, x, y, z) {
         r <- comets::gcm(a$x, a$y, a$z, reg_YonZ = "lrm", reg_XonZ = "lrm", type = "scalar")
         list(stat = unname(r$statistic), p = unname(r$p.value))
       })
}
# Rfast wants 0-based codes, the number of levels of each column and 1-based column indices.
# Its C++ code takes a double matrix and a double vector. The factory converts the codes and the level
# counts to double (setup). An integer matrix would make Rfast copy the whole matrix in every call.
# Rfast returns the statistic and the degrees of freedom. The p-value belongs to the timed call.
rfast_disc <- function(fun) {
  function() {
    dmat <- as.matrix(d)
    storage.mode(dmat) <- "double"  # 0-based codes, as written by data.py
    dc <- as.numeric(nlev)
    list(prepare = function(x, y, z) list(x = ix[[x]], y = ix[[y]], z = as.numeric(unname(ix[z]))),
         run = function(a, x, y, z) {
           r <- fun(dmat, a$x, a$y, a$z, dc)
           list(stat = r$statistic, p = pchisq(r$statistic, r$df, lower.tail = FALSE))
         })
  }
}
fc <- function(ctor, df) {
  function() {
    t <- ctor(fastcit::dataset(df))
    function(x, y, z) { r <- fastcit::run_test(t, x, y, z); list(stat = r$statistic, p = r$p_value) }
  }
}

noop <- function() function(x, y, z) list(stat = 0, p = 1)  # the harness floor

new_state <- function(n) {
  list(best = rep(Inf, n), ps = rep(NA_real_, n), st = rep(NA_real_, n), err = rep(FALSE, n),
       nan = rep(FALSE, n), totals = numeric(0), setups = numeric(0))
}

# Time one pass of one engine: build its state (setup), then run every query once. Returns the new state.
time_pass <- function(factory, qs, s, first) {
  invisible(gc(full = TRUE))  # outside the timer
  t0 <- Sys.time()
  run <- factory()  # new objects each pass, so no state carries over
  setup <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
  total <- setup
  for (i in seq_along(qs)) {
    q <- qs[[i]]; z <- as.character(unlist(q$z))
    arg <- if (is.list(run)) run$prepare(q$x, q$y, z) else NULL  # not timed
    t0 <- Sys.time()
    r <- tryCatch(if (is.list(run)) run$run(arg, q$x, q$y, z) else run(q$x, q$y, z), error = function(e) {
      if (!s$err[i]) message("  error: ", conditionMessage(e))
      NULL
    })
    dt <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
    total <- total + dt
    s$best[i] <- min(s$best[i], dt)
    if (is.null(r)) s$err[i] <- TRUE
    else if (!is.finite(r$p)) s$nan[i] <- TRUE
    if (first && !is.null(r)) {
      s$ps[i] <- if (is.finite(r$p)) r$p else NA_real_
      if (!is.null(r$stat) && is.finite(r$stat)) s$st[i] <- r$stat
    }
  }
  s$totals <- c(s$totals, total); s$setups <- c(s$setups, setup)
  s
}

result <- function(s) {
  ok <- !s$err & !s$nan
  list(median_ms = if (any(ok)) 1e3 * median(s$best[ok]) else NA, total_ms = 1e3 * min(s$totals),
       setup_ms = 1e3 * min(s$setups), n_queries = length(s$best), n_timed = sum(ok), errors = sum(s$err),
       nan = sum(s$nan), ms = 1e3 * s$best, p = s$ps, stat = s$st)
}

# Run PASSES passes over the engines of one row. The passes are the outer loop. orders[[pass]] gives the
# engine order of each pass, so that a slow period of the machine does not hit one engine only.
time_row <- function(engines, qs, orders) {
  states <- lapply(engines, function(e) new_state(length(qs)))
  for (pass in seq_len(PASSES)) {
    for (eng in orders[[pass]]) states[[eng]] <- time_pass(engines[[eng]], qs, states[[eng]], pass == 1L)
  }
  lapply(states, result)
}

d <- read_data("discrete"); dfac <- as.data.frame(lapply(d, factor)); dint <- as.data.frame(lapply(d, as.integer))
ix <- setNames(seq_along(d), names(d)); nlev <- sapply(d, function(c) length(unique(c)))
pc_disc <- function(adapt) function() {
  ss <- list(dm = as.matrix(d), nlev = nlev, adaptDF = adapt)
  function(x, y, z) list(p = pcalg::disCItest(ix[[x]], ix[[y]], unname(ix[z]), ss))
}
stopifnot(min(as.matrix(d)) == 0)  # Rfast needs 0-based codes; it crashes R when the codes start at 1
g <- read_data("gaussian"); gi <- setNames(seq_along(g), names(g))
h <- read_data("hsic")

ROWS <- list(
  chi_square = list(group = "discrete", label = "chi-squared", engines = list(
    fastcit = fc(function(ds) fastcit::chi_squared(ds, yates = FALSE), dint),
    bnlearn = function() bn_subset(dfac, "x2"),
    `bnlearn (adf)` = function() bn_subset(dfac, "x2-adf"),
    Rfast = rfast_disc(Rfast::chi2Test))),
  g_sq = list(group = "discrete", label = "G-squared", engines = list(
    fastcit = fc(function(ds) fastcit::log_likelihood(ds, yates = FALSE), dint),
    pcalg = pc_disc(FALSE),
    `pcalg (adaptDF)` = pc_disc(TRUE),
    bnlearn = function() bn_subset(dfac, "mi"),
    `bnlearn (adf)` = function() bn_subset(dfac, "mi-adf"),
    Rfast = rfast_disc(Rfast::g2Test))),
  fisher_z = list(group = "gaussian", label = "Fisher-z", engines = list(
    fastcit = fc(fastcit::fisher_z, g),
    pcalg = function() {
      ss <- list(C = cor(g), n = nrow(g))  # the correlation matrix is built once, outside the timer
      function(x, y, z) list(p = pcalg::gaussCItest(gi[[x]], gi[[y]], unname(gi[z]), ss))
    },
    bnlearn = function() bn_subset(g, "zf"))),
  pearson_t = list(group = "gaussian", label = "Pearson t", engines = list(
    fastcit = fc(fastcit::pearson_correlation, g),
    bnlearn = function() bn_subset(g, "cor"),
    ppcor = function() ppcor_cols(g))),
  hsic = list(group = "hsic", label = "HSIC (median width)", engines = list(
    fastcit = fc(function(ds) fastcit::hsic(ds, bandwidth = "median"), h),
    dHSIC = function() function(x, y, z) {
      r <- dHSIC::dhsic.test(h[[x]], h[[y]], method = "gamma", kernel = "gaussian")
      list(stat = r$statistic, p = r$p.value)
    })),
  gcm = list(group = "gcm", label = "GCM", engines = list(
    fastcit = fc(fastcit::gcm, g),
    comets = function() comets_gcm(g)))
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
# Tree hashes stay valid after a squash merge. Check them with `git rev-parse <commit>:<path>`.
fastcit_trees <- function() {
  env <- sub("-dirty$", "", Sys.getenv("FASTCIT_COMMIT", ""))
  rev <- if (nzchar(env)) env else "HEAD"
  paths <- c("crates/ci-core", "crates/ci-r")
  out <- lapply(paths, function(p) {
    h <- sh(paste("git -C", shQuote(script_dir), "rev-parse", shQuote(paste0(rev, ":", p))))
    if (nzchar(h)) h else "unknown"
  })
  setNames(out, paths)
}
env_threads <- Filter(nzchar, Sys.getenv(c("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")))
affinity <- tryCatch({
  l <- readLines("/proc/self/status"); trimws(sub("^Cpus_allowed_list:", "", grep("^Cpus_allowed_list", l, value = TRUE)))
}, error = function(e) "")
read_line <- function(path) tryCatch(trimws(readLines(path, n = 1L, warn = FALSE)), error = function(e) "unknown")
# The power state: AC adapter, power profile, and the governor and EPP of CPU 0 (Linux).
power_state <- function() {
  supplies <- Sys.glob("/sys/class/power_supply/*")
  mains <- supplies[vapply(supplies, function(p) identical(read_line(file.path(p, "type")), "Mains"), logical(1))]
  cpu0 <- "/sys/devices/system/cpu/cpu0/cpufreq"
  profile <- sh("powerprofilesctl get 2>/dev/null")
  list(ac_online = if (length(mains)) read_line(file.path(mains[1], "online")) else "unknown",
       profile = if (nzchar(profile)) profile else "unknown",
       governor = read_line(file.path(cpu0, "scaling_governor")),
       epp = read_line(file.path(cpu0, "energy_performance_preference")))
}
meta <- list(
  date = format(Sys.time(), "%Y-%m-%d %H:%M:%S"), cpu = cpu, logical_cpus = parallel::detectCores(),
  os = paste(Sys.info()[["sysname"]], Sys.info()[["release"]]), r = R.version.string, quick = quick,
  passes = PASSES, seed = seed, uptime_start = sh("uptime"), power = power_state(),
  affinity = list(cpus_allowed_list = affinity),
  versions = list(fastcit = as.character(packageVersion("fastcit")), pcalg = as.character(packageVersion("pcalg")),
                  bnlearn = as.character(packageVersion("bnlearn")), dHSIC = as.character(packageVersion("dHSIC")),
                  Rfast = as.character(packageVersion("Rfast")), ppcor = as.character(packageVersion("ppcor")),
                  comets = as.character(packageVersion("comets"))),
  commits = list(fastcit = fastcit_commit()), fastcit_trees = fastcit_trees(),
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
