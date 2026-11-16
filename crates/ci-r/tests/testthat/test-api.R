# Surface tests for the data-bound R API: dataset binding, result shapes,
# factor coding, the equivalence decision inversion, error handling, the htest
# adapter, and the pcalg closure.

library(cir)

discrete_df <- function() {
  set.seed(0)
  data.frame(
    A = sample(0:1, 200, TRUE),
    B = sample(0:1, 200, TRUE),
    C = sample(0:2, 200, TRUE)
  )
}

continuous_df <- function() {
  set.seed(1)
  data.frame(
    X = rnorm(200),
    Y = rnorm(200),
    Z = rnorm(200)
  )
}

test_that("dataset() infers kinds and reports shape / index", {
  data <- dataset(discrete_df())
  expect_s3_class(data, "cir_dataset")
  expect_equal(data$ptr$n_rows(), 200L)
  expect_equal(data$ptr$n_cols(), 3L)
  expect_equal(data$ptr$index_of("A"), 1L) # 1-based
  expect_equal(data$ptr$index_of("C"), 3L)
  expect_true(is.na(data$ptr$index_of("nope")))
  expect_equal(data$kinds, c("discrete", "discrete", "discrete"))
})

test_that("continuous columns are inferred as continuous", {
  data <- dataset(continuous_df())
  expect_equal(unname(data$kinds), c("continuous", "continuous", "continuous"))
})

test_that("run_test returns the uniform list for discrete tests", {
  chi <- chi_squared(dataset(discrete_df()))
  res <- run_test(chi, "A", "B")
  expect_named(res, c("statistic", "p_value", "dof", "effect_size"))
  expect_true(is.numeric(res$statistic))
  expect_true(is.numeric(res$p_value))
  expect_true(is.numeric(res$dof))
})

test_that("z defaults to an empty conditioning set", {
  chi <- chi_squared(dataset(discrete_df()))
  expect_equal(
    run_test(chi, "A", "B")$p_value,
    run_test(chi, "A", "B", character())$p_value
  )
})

test_that("conditioning on a name works", {
  chi <- chi_squared(dataset(discrete_df()))
  res <- run_test(chi, "A", "C", c("B"))
  expect_true(is.numeric(res$p_value))
})

test_that("is_independent returns a single logical", {
  chi <- chi_squared(dataset(discrete_df()))
  out <- is_independent(chi, "A", "C", c("B"), significance_level = 0.05)
  expect_true(is.logical(out))
  expect_length(out, 1L)
})

test_that("is_independent rejects non-finite significance levels", {
  chi <- chi_squared(dataset(discrete_df()))
  for (level in c(NaN, Inf, -Inf)) {
    expect_error(
      is_independent(chi, "A", "B", significance_level = level),
      "significance level must be finite"
    )
  }
})

test_that("pearson_equivalence has NULL dof and the inverted rule", {
  eqv <- pearson_equivalence(dataset(continuous_df()), delta_threshold = 0.1)
  res <- run_test(eqv, "X", "Y", c("Z"))
  expect_null(res$dof)
  expect_true(is.numeric(res$p_value))
  # The equivalence rule is independent <=> p < alpha. With alpha = 1 every
  # finite p-value is < 1, so it must report independent; with alpha = 0 none
  # can be, so it must report dependent. This pins the inversion direction.
  expect_true(is_independent(eqv, "X", "Y", c("Z"), significance_level = 1))
  expect_false(is_independent(eqv, "X", "Y", c("Z"), significance_level = 0))
})

test_that("the standard rule is the non-inverted direction", {
  chi <- chi_squared(dataset(discrete_df()))
  # Standard rule: independent <=> p >= alpha. alpha = 0 => always independent;
  # alpha = 1 => never (finite p < 1).
  expect_true(
    is_independent(chi, "A", "B", character(), significance_level = 0)
  )
  expect_false(
    is_independent(chi, "A", "B", character(), significance_level = 1)
  )
})

test_that("pearson_correlation takes no config", {
  res <- run_test(pearson_correlation(dataset(continuous_df())), "X", "Y")
  # The Pearson correlation t-test reports dof = n - |Z| - 2 (here 200 - 0 - 2).
  expect_equal(res$dof, 198L)
  expect_true(is.numeric(res$p_value))
})

test_that("factory functions accept a raw data.frame", {
  chi <- chi_squared(discrete_df())
  expect_s3_class(chi, "cir_test")
  expect_true(is.numeric(run_test(chi, "A", "B")$p_value))
})

test_that("factor and character columns are coded to discrete", {
  set.seed(3)
  df <- data.frame(
    F = factor(sample(c("a", "b", "c"), 200, TRUE)),
    G = sample(c("yes", "no"), 200, TRUE),
    stringsAsFactors = FALSE
  )
  data <- dataset(df)
  expect_equal(unname(data$kinds), c("discrete", "discrete"))
  res <- run_test(chi_squared(data), "F", "G")
  expect_true(is.numeric(res$statistic))
  # A three-by-two table has (3 - 1) * (2 - 1) degrees of freedom.
  expect_equal(res$dof, 2L)
})

test_that("a dataset can be shared across tests", {
  data <- dataset(continuous_df())
  a <- run_test(pearson_correlation(data), "X", "Y")
  b <- run_test(pearson_equivalence(data, delta_threshold = 0.2), "X", "Y")
  expect_true(is.numeric(a$p_value))
  expect_true(is.numeric(b$p_value))
})

test_that("unknown column names raise an error", {
  chi <- chi_squared(dataset(discrete_df()))
  expect_error(run_test(chi, "A", "nope"), "unknown column")
})

test_that("a continuous column handed to a discrete test errors", {
  chi <- chi_squared(dataset(continuous_df()))
  expect_error(run_test(chi, "X", "Y"), "wrong column kind")
})

test_that("ci_test returns an htest with statistic, parameter, p.value", {
  chi <- chi_squared(dataset(discrete_df()))
  # Unconditional 2x2 table (A, B both binary) => dof = (2-1)*(2-1) = 1.
  h <- ci_test(chi, "A", "B")
  expect_s3_class(h, "htest")
  expect_true(is.numeric(h$statistic))
  expect_equal(unname(h$parameter), 1)
  expect_true(is.numeric(h$p.value))
})

test_that("as_pcalg returns a (x, y, S, suffStat) -> p.value closure", {
  data <- dataset(continuous_df())
  indep <- as_pcalg(pearson_correlation(data))
  expect_type(indep, "closure")
  # 1-based node indices into the bound columns (X=1, Y=2, Z=3).
  p_uncond <- indep(1, 2, integer(0), list())
  p_cond <- indep(1, 2, c(3L), list())
  expect_true(is.numeric(p_uncond) && length(p_uncond) == 1L)
  expect_true(is.numeric(p_cond) && length(p_cond) == 1L)
  # Matches the direct run_test p-value.
  expect_equal(p_uncond, run_test(pearson_correlation(data), "X", "Y")$p_value)
})

test_that("as_pcalg uses the native rule rather than the display name", {
  data <- dataset(continuous_df())
  equivalence <- pearson_equivalence(data)
  equivalence$name <- "renamed_equivalence"
  expect_error(as_pcalg(equivalence), "inverted decision rule")

  standard <- fisher_z(data)
  standard$name <- "pearson_equivalence"
  callback <- as_pcalg(standard)
  expect_equal(
    callback(1, 2, integer(), list()),
    run_test(standard, "X", "Y")$p_value
  )
})

test_that("fisher_z runs and reports no dof", {
  set.seed(11)
  n <- 80
  z <- rnorm(n)
  df <- data.frame(
    X = 1.2 * z + 0.4 * rnorm(n),
    Y = 0.7 * z + 0.4 * rnorm(n),
    Z = z
  )
  fz <- fisher_z(dataset(df))
  res <- run_test(fz, "X", "Y", c("Z"))
  expect_null(res$dof)
  expect_true(res$p_value >= 0 && res$p_value <= 1)
  # statistic = sqrt(n - |Z| - 3) * atanh(r)
  pc <- run_test(pearson_correlation(dataset(df)), "X", "Y", c("Z"))
  expect_equal(
    res$statistic,
    sqrt(n - 1 - 3) * atanh(pc$statistic),
    tolerance = 1e-9
  )
})

test_that("NA values error at dataset construction", {
  df <- data.frame(A = c(1L, NA_integer_, 0L), X = c(0.1, 0.2, 0.3))
  expect_error(dataset(df), "missing data")
  df2 <- data.frame(A = c(0L, 1L, 0L), X = c(0.1, NA_real_, 0.3))
  expect_error(dataset(df2), "missing data")
  df3 <- data.frame(A = factor(c("u", NA, "v")), X = c(0.1, 0.2, 0.3))
  expect_error(dataset(df3), "missing data")
  # Character columns are coded via a separate branch of .cir_code_column.
  df4 <- data.frame(
    A = c("u", NA, "v"), X = c(0.1, 0.2, 0.3),
    stringsAsFactors = FALSE
  )
  expect_error(dataset(df4), "missing data")
})

test_that("invalid queries error", {
  df <- data.frame(
    A = sample(0:1, 40, TRUE),
    B = sample(0:1, 40, TRUE),
    C = sample(0:1, 40, TRUE)
  )
  chi <- chi_squared(dataset(df))
  expect_error(run_test(chi, "A", "A"), "invalid query")
  expect_error(run_test(chi, "A", "B", c("A")), "invalid query")
  expect_error(run_test(chi, "A", "B", c("C", "C")), "invalid query")
})

# ---------------------------------------------------------------------------
# HSIC and KCI
# ---------------------------------------------------------------------------

kernel_df <- function() {
  set.seed(3)
  x <- rnorm(60)
  data.frame(X = x, Y = x^2 + rnorm(60, sd = 0.3), Z = rnorm(60))
}

test_that("kernel constructors build cir_kernel objects", {
  rbf <- rbf_kernel(2)
  expect_s3_class(rbf, "cir_kernel")
  expect_equal(rbf$type, "rbf")
  expect_equal(rbf$length_scale, 2)
  expect_equal(linear_kernel()$type, "linear")
  expect_output(print(rbf), "rbf")
  expect_output(print(linear_kernel()), "linear")
  expect_error(rbf_kernel(0))
  expect_error(rbf_kernel(-1))
  expect_error(rbf_kernel(NA_real_))
  expect_error(rbf_kernel("a"))
})

test_that("hsic and kci report meta; hsic is symmetric", {
  data <- dataset(kernel_df())
  h <- hsic(data)
  k <- kci(data)
  expect_s3_class(h, "cir_test")
  expect_s3_class(k, "cir_test")
  expect_equal(h$name, "hsic")
  expect_equal(k$name, "kci")
  expect_equal(h$handle$decision_rule(), "p_value_ge")
  expect_equal(k$handle$decision_rule(), "p_value_ge")
  expect_equal(
    run_test(h, "X", "Y")$p_value,
    run_test(h, "Y", "X")$p_value,
    tolerance = 1e-9
  )
  # KCI is not exactly symmetric (its core meta says so); both orders run.
  expect_true(is.finite(run_test(k, "X", "Y", "Z")$p_value))
  expect_true(is.finite(run_test(k, "Y", "X", "Z")$p_value))
})

test_that("a kernel object and the equivalent named list agree", {
  data <- dataset(kernel_df())
  all_k <- run_test(hsic(data, kernel = rbf_kernel(1.5)), "X", "Y")
  per_col <- run_test(
    hsic(data, kernel = list(X = rbf_kernel(1.5), Y = rbf_kernel(1.5))),
    "X", "Y"
  )
  expect_equal(all_k$p_value, per_col$p_value, tolerance = 1e-12)
  expect_equal(all_k$statistic, per_col$statistic, tolerance = 1e-12)
})

test_that("permutation null is deterministic for a seed", {
  data <- dataset(kernel_df())
  t1 <- hsic(data, null_dist = "permutation", n_permutations = 20L, seed = 5)
  t2 <- hsic(data, null_dist = "permutation", n_permutations = 20L, seed = 5)
  expect_equal(run_test(t1, "X", "Y")$p_value, run_test(t2, "X", "Y")$p_value)
})

test_that("hsic and kci reject invalid configuration", {
  data <- dataset(kernel_df())
  expect_error(hsic(data, kernel = list(Nope = rbf_kernel(1))), "Nope")
  expect_error(kci(data, kernel = list(Nope = linear_kernel())), "Nope")
  expect_error(hsic(data, bandwidth = "x"))
  expect_error(kci(data, bandwidth = "x"))
  expect_error(hsic(data, null_dist = "x"))
  expect_error(hsic(data, null_dist = "permutation", seed = -1))
  expect_error(hsic(data, null_dist = "permutation", seed = 1.5))
  expect_error(hsic(data, seed = NA_real_))
  expect_error(hsic(data, seed = Inf))
  expect_error(hsic(data, seed = 2^53 + 2))
  expect_error(hsic(data, n_permutations = 0))
  expect_error(hsic(data, n_permutations = 2.5))
  expect_error(hsic(data, n_permutations = NA_integer_))
  expect_error(hsic(data, null_dist = "permutation", n_permutations = 0))
  expect_error(kci(data, epsilon = 0))
  expect_error(kci(data, epsilon = -1))
  expect_error(hsic(data, kernel = "rbf"))
  expect_error(kci(data, kernel = "rbf"))
  expect_error(hsic(data, kernel = list(X = "rbf")))
  expect_error(hsic(data, kernel = list(rbf_kernel(1))))
})

test_that("hsic rejects a conditioning set", {
  data <- dataset(kernel_df())
  expect_error(run_test(hsic(data), "X", "Y", "Z"))
})
