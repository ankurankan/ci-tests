#' Build a `fastcit_test` wrapper around a constructed extendr test handle.
#'
#' @param handle The external-pointer test handle from `<Class>$new(...)`.
#' @param ds The bound `fastcit_dataset` (carries column names for pcalg mapping).
#' @param name The test's stable name (e.g. `"chi_squared"`).
#' @return An object of class `fastcit_test`.
#' @keywords internal
.fastcit_make_test <- function(handle, ds, name) {
  structure(
    list(handle = handle, dataset = ds, name = name),
    class = "fastcit_test"
  )
}

#' Chi-squared (Pearson, lambda = 1) discrete CI test.
#'
#' @param data A [dataset()] result or a data.frame.
#' @param yates Whether to apply Yates' continuity correction on 2x2
#'   sub-tables (default `TRUE`, the scipy/pgmpy convention).
#' @return A `fastcit_test` bound to `data`.
#' @examples
#' df <- data.frame(A = sample(0:1, 80, TRUE), B = sample(0:1, 80, TRUE))
#' chi <- chi_squared(dataset(df))
#' run_test(chi, "A", "B")
#' @export
chi_squared <- function(data, yates = TRUE) {
  ds <- .fastcit_as_dataset(data)
  .fastcit_make_test(
    ChiSquared$new(ds$ptr, yates), # nolint: object_usage_linter.
    ds,
    "chi_squared"
  )
}

#' Log-likelihood / G-test (lambda = 0) discrete CI test.
#'
#' @inheritParams chi_squared
#' @return A `fastcit_test` bound to `data`.
#' @export
log_likelihood <- function(data, yates = TRUE) {
  ds <- .fastcit_as_dataset(data)
  .fastcit_make_test(
    LogLikelihood$new(ds$ptr, yates), # nolint: object_usage_linter.
    ds,
    "log_likelihood"
  )
}

#' Cressie-Read (lambda = 2/3) discrete CI test.
#'
#' @inheritParams chi_squared
#' @return A `fastcit_test` bound to `data`.
#' @export
cressie_read <- function(data, yates = TRUE) {
  ds <- .fastcit_as_dataset(data)
  .fastcit_make_test(
    CressieRead$new(ds$ptr, yates), # nolint: object_usage_linter.
    ds,
    "cressie_read"
  )
}

#' Freeman-Tukey (lambda = -1/2) discrete CI test.
#'
#' @inheritParams chi_squared
#' @return A `fastcit_test` bound to `data`.
#' @export
freeman_tukey <- function(data, yates = TRUE) {
  ds <- .fastcit_as_dataset(data)
  .fastcit_make_test(
    FreemanTukey$new(ds$ptr, yates), # nolint: object_usage_linter.
    ds,
    "freeman_tukey"
  )
}

#' Modified log-likelihood (lambda = -1) discrete CI test.
#'
#' @inheritParams chi_squared
#' @return A `fastcit_test` bound to `data`.
#' @export
modified_likelihood <- function(data, yates = TRUE) {
  ds <- .fastcit_as_dataset(data)
  .fastcit_make_test(
    ModifiedLikelihood$new(ds$ptr, yates), # nolint: object_usage_linter.
    ds,
    "modified_likelihood"
  )
}

#' Pearson partial-correlation continuous CI test.
#'
#' @param data A [dataset()] result or a data.frame.
#' @return A `fastcit_test` bound to `data`.
#' @export
pearson_correlation <- function(data) {
  ds <- .fastcit_as_dataset(data)
  .fastcit_make_test(
    PearsonCorrelation$new(ds$ptr), # nolint: object_usage_linter.
    ds,
    "pearson_correlation"
  )
}

#' Fisher-z continuous CI test.
#'
#' Applies the Fisher z-transform to the (partial) correlation:
#' `sqrt(n - |Z| - 3) * atanh(rho)` is approximately standard normal under
#' independence. This matches `pcalg::gaussCItest`'s statistic and is the
#' de-facto standard continuous CI test in constraint-based causal discovery.
#'
#' @param data A [dataset()] result or a data.frame.
#' @return A `fastcit_test` bound to `data`.
#' @export
fisher_z <- function(data) {
  ds <- .fastcit_as_dataset(data)
  .fastcit_make_test(
    FisherZ$new(ds$ptr), # nolint: object_usage_linter.
    ds,
    "fisher_z"
  )
}

#' Generalised covariance measure (GCM) continuous CI test.
#'
#' Residualizes `X` and `Y` on the conditioning variables with linear
#' regression, then tests the mean of the product of the residuals with a
#' studentised z statistic. Only continuous columns are supported: a factor
#' column raises a "wrong column kind" error. Degenerate inputs raise errors
#' rather than returning `NaN`. Conditioning sets whose columns are linearly
#' dependent (duplicate or nested categorical variables, a constant column)
#' raise a degenerate-data error, whereas pgmpy fits them by least squares.
#'
#' @param data A [dataset()] result or a data.frame.
#' @return A `fastcit_test` bound to `data`.
#' @examples
#' set.seed(1)
#' df <- data.frame(Z = rnorm(100))
#' df$X <- df$Z + rnorm(100)
#' df$Y <- df$Z + rnorm(100)
#' run_test(gcm(df), "X", "Y", "Z")
#' @export
gcm <- function(data) {
  ds <- .fastcit_as_dataset(data)
  .fastcit_make_test(
    GCM$new(ds$ptr), # nolint: object_usage_linter.
    ds,
    "gcm"
  )
}

#' Pillai trace CI test for mixed data.
#'
#' Residualizes `X` and `Y` on the conditioning variables with linear
#' regression (pgmpy's Pillai default is a random forest) and computes the
#' Pillai trace from the exact canonical correlations of the residuals.
#' Conditioning variables are one-hot encoded minus one level. A categorical
#' `X` or `Y` becomes `K - 1` level indicators, residualized with a linear
#' probability model. Factor and numeric columns may be mixed. Degenerate
#' inputs raise errors instead of returning `NaN`. Conditioning sets whose columns are linearly
#' dependent (duplicate or nested categorical variables, a constant column)
#' raise a degenerate-data error, whereas pgmpy fits them by least squares.
#' With few rows relative to the conditioning columns and categorical levels
#' (`n - columns < p + q`), the test returns `p = 0` ("dependent"), as pgmpy
#' does.
#'
#' @param data A [dataset()] result or a data.frame.
#' @return A `fastcit_test` bound to `data`.
#' @examples
#' set.seed(1)
#' df <- data.frame(
#'   X = factor(sample(c("a", "b", "c"), 100, TRUE)),
#'   Y = rnorm(100),
#'   Z = rnorm(100)
#' )
#' run_test(pillai(df), "X", "Y", "Z")
#' @export
pillai <- function(data) {
  ds <- .fastcit_as_dataset(data)
  .fastcit_make_test(
    Pillai$new(ds$ptr), # nolint: object_usage_linter.
    ds,
    "pillai"
  )
}

#' Pearson equivalence (TOST) continuous CI test.
#'
#' Declares independence when the partial correlation is within the equivalence
#' margin. Note the inverted decision rule: independence holds when the p-value
#' is **below** the significance level (handled by [is_independent()]).
#'
#' @param data A [dataset()] result or a data.frame.
#' @param delta_threshold Equivalence margin on the correlation scale
#'   (default `0.1`).
#' @return A `fastcit_test` bound to `data`.
#' @export
pearson_equivalence <- function(data, delta_threshold = 0.1) {
  ds <- .fastcit_as_dataset(data)
  .fastcit_make_test(
    # extendr generates this constructor in a separate source file.
    PearsonEquivalence$new( # nolint: object_usage_linter.
      ds$ptr, delta_threshold
    ),
    ds,
    "pearson_equivalence"
  )
}

#' Radial-basis-function (Gaussian) kernel specification.
#'
#' @param length_scale Positive, finite length scale of the kernel.
#' @return A `fastcit_kernel` object for use as the `kernel` argument of [hsic()]
#'   and [kci()].
#' @examples
#' rbf_kernel(2)
#' @export
rbf_kernel <- function(length_scale) {
  bad <- !is.numeric(length_scale) || length(length_scale) != 1L
  bad <- bad || !is.finite(length_scale) || length_scale <= 0
  if (bad) {
    stop(
      "`length_scale` must be a single positive finite number",
      call. = FALSE
    )
  }
  structure(
    list(type = "rbf", length_scale = as.double(length_scale)),
    class = "fastcit_kernel"
  )
}

#' Linear kernel specification.
#'
#' @return A `fastcit_kernel` object for use as the `kernel` argument of [hsic()]
#'   and [kci()].
#' @examples
#' linear_kernel()
#' @export
linear_kernel <- function() {
  structure(list(type = "linear"), class = "fastcit_kernel")
}

#' @export
print.fastcit_kernel <- function(x, ...) {
  if (identical(x$type, "rbf")) {
    cat(sprintf(
      "<fastcit_kernel: rbf, length_scale = %s>\n",
      format(x$length_scale)
    ))
  } else {
    cat("<fastcit_kernel: linear>\n")
  }
  invisible(x)
}

#' Flatten a `kernel` argument for the extendr layer.
#'
#' @param kernel `NULL`, one `fastcit_kernel`, or a named list of `fastcit_kernel`.
#' @return A list with `mode`, `names`, `types` and `length_scales`.
#' @keywords internal
.fastcit_flatten_kernel <- function(kernel) {
  flat <- function(k) {
    if (!inherits(k, "fastcit_kernel")) {
      stop(
        "`kernel` must be NULL, a fastcit_kernel, or a named list of fastcit_kernel",
        call. = FALSE
      )
    }
    list(
      type = k$type,
      length_scale = if (identical(k$type, "rbf")) k$length_scale else NA_real_
    )
  }
  pack <- function(mode, names, ks) {
    list(
      mode = mode,
      names = as.character(names),
      types = vapply(ks, function(k) k$type, character(1)),
      length_scales = vapply(ks, function(k) k$length_scale, double(1))
    )
  }
  if (is.null(kernel)) {
    return(list(
      mode = "auto", names = character(), types = character(),
      length_scales = double()
    ))
  }
  if (inherits(kernel, "fastcit_kernel")) {
    return(pack("all", "", list(flat(kernel))))
  }
  nms <- names(kernel)
  bad <- !is.list(kernel) || length(kernel) == 0L || is.null(nms)
  bad <- bad || anyNA(nms) || any(!nzchar(nms)) || anyDuplicated(nms) > 0L
  if (bad) {
    stop(
      "`kernel` must be NULL, a fastcit_kernel, or a named list of fastcit_kernel",
      call. = FALSE
    )
  }
  pack("per_column", nms, lapply(unname(kernel), flat))
}

#' Hilbert-Schmidt Independence Criterion (HSIC) CI test.
#'
#' A kernel independence test for `x` and `y` with no conditioning set;
#' [run_test()] errors if `z` is non-empty (use [kci()] to condition).
#'
#' @param data A [dataset()] result or a data.frame.
#' @param kernel `NULL` (default RBF kernel), one [rbf_kernel()] /
#'   [linear_kernel()] used for every column, or a named list of such kernels
#'   keyed by column name.
#' @param bandwidth Bandwidth rule, `"heuristic"` (default) or `"median"`.
#' @param null_dist Null distribution, `"gamma"` (default) or `"permutation"`.
#' @param n_permutations Number of permutations (whole number >= 1); unused
#'   with the gamma null but always validated.
#' @param seed Permutation seed (whole number, 0 to 2^53); unused with the
#'   gamma null.
#' @return A `fastcit_test` bound to `data`.
#' @examples
#' df <- data.frame(X = rnorm(50), Y = rnorm(50))
#' run_test(hsic(dataset(df)), "X", "Y")
#' @export
hsic <- function(
  data,
  kernel = NULL,
  bandwidth = "heuristic",
  null_dist = "gamma",
  n_permutations = 100L,
  seed = 0
) {
  ds <- .fastcit_as_dataset(data)
  k <- .fastcit_flatten_kernel(kernel)
  .fastcit_make_test(
    HSIC$new( # nolint: object_usage_linter.
      ds$ptr, k$mode, k$names, k$types, k$length_scales,
      bandwidth, null_dist, .fastcit_as_count(n_permutations, "n_permutations"),
      .fastcit_as_count(seed, "seed")
    ),
    ds,
    "hsic"
  )
}

#' Kernel-based conditional independence (KCI) test.
#'
#' @inheritParams hsic
#' @param epsilon Positive regularisation parameter (default `1e-3`).
#' @return A `fastcit_test` bound to `data`.
#' @examples
#' df <- data.frame(X = rnorm(50), Y = rnorm(50), Z = rnorm(50))
#' run_test(kci(dataset(df)), "X", "Y", "Z")
#' @export
kci <- function(
  data,
  kernel = NULL,
  bandwidth = "heuristic",
  epsilon = 1e-3
) {
  ds <- .fastcit_as_dataset(data)
  k <- .fastcit_flatten_kernel(kernel)
  .fastcit_make_test(
    KCI$new( # nolint: object_usage_linter.
      ds$ptr, k$mode, k$names, k$types, k$length_scales,
      bandwidth, epsilon
    ),
    ds,
    "kci"
  )
}

#' Coerce a count/seed argument to a double scalar for the extendr layer.
#'
#' @param x The user-supplied value.
#' @param name Argument name for the error message.
#' @return A length-1 double (range and wholeness are checked in Rust).
#' @keywords internal
.fastcit_as_count <- function(x, name) {
  if (!is.numeric(x) || length(x) != 1L) {
    stop(sprintf("`%s` must be a single number", name), call. = FALSE)
  }
  as.double(x)
}

#' @export
print.fastcit_test <- function(x, ...) {
  cat(sprintf("<fastcit_test: %s>\n", x$name))
  invisible(x)
}

# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

#' Run a conditional-independence test.
#'
#' @param test A `fastcit_test` from one of the factory functions.
#' @param x,y Column **names** (length-1 character) for the two variables.
#' @param z Character vector of conditioning column names (default: none).
#' @return A named list `list(statistic, p_value, dof, effect_size)`; absent
#'   fields are `NULL`.
#' @examples
#' df <- data.frame(A = sample(0:1, 80, TRUE), B = sample(0:1, 80, TRUE))
#' run_test(chi_squared(dataset(df)), "A", "B")
#' @export
run_test <- function(test, x, y, z = character()) {
  stopifnot(inherits(test, "fastcit_test"))
  test$handle$run_test(x, y, .fastcit_as_names(z))
}

#' Decide conditional independence at a significance level.
#'
#' Applies the test's own decision rule: `p >= significance_level` for the
#' standard tests, and the inverted `p < significance_level` for
#' [pearson_equivalence()].
#'
#' @param test A `fastcit_test` from one of the factory functions.
#' @param x,y Column names for the two variables.
#' @param z Character vector of conditioning column names (default: none).
#' @param significance_level Significance level alpha (default `0.05`).
#' @return A single logical: `TRUE` if independent at `significance_level`.
#' @export
is_independent <- function(
  test,
  x,
  y,
  z = character(),
  significance_level = 0.05
) {
  stopifnot(inherits(test, "fastcit_test"))
  test$handle$is_independent(x, y, .fastcit_as_names(z), significance_level)
}

#' Normalize a conditioning-set argument to a character vector.
#'
#' Accepts `NULL`, a character vector, or a single name; never a non-character.
#'
#' @param z The `z` argument as supplied by the caller.
#' @return A character vector (possibly empty).
#' @keywords internal
.fastcit_as_names <- function(z) {
  if (is.null(z)) {
    character()
  } else if (is.character(z)) {
    z
  } else {
    stop("`z` must be a character vector of column names", call. = FALSE)
  }
}
