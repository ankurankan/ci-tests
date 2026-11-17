# The engines, the timing core and the metadata helpers of the R benchmarks.
# benchmarks/bench_r.R (one fixed dataset per test) and benchmarks/sweep_r.R (a grid of n and |Z|) source this file.
# An engine factory is a function of the data, so that a sweep point can build its engines on the first n rows.

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
rfast_disc <- function(fun, d, ix, nlev) {
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

# The existing rows, in three groups by data. d is the discrete data (0-based integer codes), g the Gaussian
# data, h the HSIC data. Each row lists its engines as factories, which build their test objects outside the timer.
discrete_rows <- function(d) {
  dfac <- as.data.frame(lapply(d, factor)); dint <- as.data.frame(lapply(d, as.integer))
  ix <- setNames(seq_along(d), names(d)); nlev <- sapply(d, function(c) length(unique(c)))
  pc_disc <- function(adapt) function() {
    ss <- list(dm = as.matrix(d), nlev = nlev, adaptDF = adapt)
    function(x, y, z) list(p = pcalg::disCItest(ix[[x]], ix[[y]], unname(ix[z]), ss))
  }
  stopifnot(min(as.matrix(d)) == 0)  # Rfast needs 0-based codes; it crashes R when the codes start at 1
  list(
    chi_square = list(group = "discrete", label = "chi-squared", engines = list(
      fastcit = fc(function(ds) fastcit::chi_squared(ds, yates = FALSE), dint),
      bnlearn = function() bn_subset(dfac, "x2"),
      `bnlearn (adf)` = function() bn_subset(dfac, "x2-adf"),
      Rfast = rfast_disc(Rfast::chi2Test, d, ix, nlev))),
    g_sq = list(group = "discrete", label = "G-squared", engines = list(
      fastcit = fc(function(ds) fastcit::log_likelihood(ds, yates = FALSE), dint),
      pcalg = pc_disc(FALSE),
      `pcalg (adaptDF)` = pc_disc(TRUE),
      bnlearn = function() bn_subset(dfac, "mi"),
      `bnlearn (adf)` = function() bn_subset(dfac, "mi-adf"),
      Rfast = rfast_disc(Rfast::g2Test, d, ix, nlev)))
  )
}
gaussian_rows <- function(g) {
  gi <- setNames(seq_along(g), names(g))
  list(
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
    gcm = list(group = "gcm", label = "GCM", engines = list(
      fastcit = fc(fastcit::gcm, g),
      comets = function() comets_gcm(g)))
  )
}
hsic_rows <- function(h) {
  list(hsic = list(group = "hsic", label = "HSIC (median width)", engines = list(
    fastcit = fc(function(ds) fastcit::hsic(ds, bandwidth = "median"), h),
    dHSIC = function() function(x, y, z) {
      r <- dHSIC::dhsic.test(h[[x]], h[[y]], method = "gamma", kernel = "gaussian")
      list(stat = r$statistic, p = r$p.value)
    })))
}
bench_rows <- function(d, g, h) {
  rows <- c(discrete_rows(d), gaussian_rows(g), hsic_rows(h))
  rows[c("chi_square", "g_sq", "fisher_z", "pearson_t", "hsic", "gcm")]
}

sh <- function(cmd) tryCatch(paste(system(cmd, intern = TRUE), collapse = " "), error = function(e) "")
cpu_name <- function() {
  cpu <- trimws(sh("grep -m1 'model name' /proc/cpuinfo | cut -d: -f2"))
  if (!nzchar(cpu)) cpu <- trimws(sh("sysctl -n machdep.cpu.brand_string"))
  if (!nzchar(cpu)) cpu <- paste("unknown", Sys.info()[["machine"]])
  cpu
}
fastcit_commit <- function(script_dir) {
  env <- Sys.getenv("FASTCIT_COMMIT", "")
  if (nzchar(env)) return(env)
  head <- sh(paste("git -C", shQuote(script_dir), "rev-parse --short HEAD"))
  if (!nzchar(head)) return("unknown")
  dirty <- sh(paste("git -C", shQuote(script_dir), "status --porcelain"))
  paste0(head, if (nzchar(dirty)) "-dirty" else "")
}
# Tree hashes stay valid after a squash merge. Check them with `git rev-parse <commit>:<path>`.
fastcit_trees <- function(script_dir) {
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
cpu_affinity <- function() tryCatch({
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
