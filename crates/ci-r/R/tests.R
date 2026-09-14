#' Build a `cir_test` wrapper around a constructed extendr test handle.
#'
#' @param handle The external-pointer test handle from `<Class>$new(...)`.
#' @param ds The bound `cir_dataset` (carries column names for pcalg mapping).
#' @param name The test's stable name (e.g. `"chi_squared"`).
#' @return An object of class `cir_test`.
#' @keywords internal
.cir_make_test <- function(handle, ds, name) {
  structure(
    list(handle = handle, dataset = ds, name = name),
    class = "cir_test"
  )
}

#' Chi-squared (Pearson, lambda = 1) discrete CI test.
#'
#' @param data A [dataset()] result or a data.frame.
#' @param yates Whether to apply Yates' continuity correction on 2x2
#'   sub-tables (default `TRUE`, the scipy/pgmpy convention).
#' @return A `cir_test` bound to `data`.
#' @examples
#' df <- data.frame(A = sample(0:1, 80, TRUE), B = sample(0:1, 80, TRUE))
#' chi <- chi_squared(dataset(df))
#' run_test(chi, "A", "B")
#' @export
chi_squared <- function(data, yates = TRUE) {
  ds <- .cir_as_dataset(data)
  .cir_make_test(
    ChiSquared$new(ds$ptr, yates), # nolint: object_usage_linter.
    ds,
    "chi_squared"
  )
}

#' Log-likelihood / G-test (lambda = 0) discrete CI test.
#'
#' @inheritParams chi_squared
#' @return A `cir_test` bound to `data`.
#' @export
log_likelihood <- function(data, yates = TRUE) {
  ds <- .cir_as_dataset(data)
  .cir_make_test(
    LogLikelihood$new(ds$ptr, yates), # nolint: object_usage_linter.
    ds,
    "log_likelihood"
  )
}

#' Cressie-Read (lambda = 2/3) discrete CI test.
#'
#' @inheritParams chi_squared
#' @return A `cir_test` bound to `data`.
#' @export
cressie_read <- function(data, yates = TRUE) {
  ds <- .cir_as_dataset(data)
  .cir_make_test(
    CressieRead$new(ds$ptr, yates), # nolint: object_usage_linter.
    ds,
    "cressie_read"
  )
}

#' Freeman-Tukey (lambda = -1/2) discrete CI test.
#'
#' @inheritParams chi_squared
#' @return A `cir_test` bound to `data`.
#' @export
freeman_tukey <- function(data, yates = TRUE) {
  ds <- .cir_as_dataset(data)
  .cir_make_test(
    FreemanTukey$new(ds$ptr, yates), # nolint: object_usage_linter.
    ds,
    "freeman_tukey"
  )
}

#' Modified log-likelihood (lambda = -1) discrete CI test.
#'
#' @inheritParams chi_squared
#' @return A `cir_test` bound to `data`.
#' @export
modified_likelihood <- function(data, yates = TRUE) {
  ds <- .cir_as_dataset(data)
  .cir_make_test(
    ModifiedLikelihood$new(ds$ptr, yates), # nolint: object_usage_linter.
    ds,
    "modified_likelihood"
  )
}

#' Pearson partial-correlation continuous CI test.
#'
#' @param data A [dataset()] result or a data.frame.
#' @return A `cir_test` bound to `data`.
#' @export
pearson_correlation <- function(data) {
  ds <- .cir_as_dataset(data)
  .cir_make_test(
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
#' @return A `cir_test` bound to `data`.
#' @export
fisher_z <- function(data) {
  ds <- .cir_as_dataset(data)
  .cir_make_test(
    FisherZ$new(ds$ptr), # nolint: object_usage_linter.
    ds,
    "fisher_z"
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
#' @return A `cir_test` bound to `data`.
#' @export
pearson_equivalence <- function(data, delta_threshold = 0.1) {
  ds <- .cir_as_dataset(data)
  .cir_make_test(
    # extendr generates this constructor in a separate source file.
    PearsonEquivalence$new( # nolint: object_usage_linter.
      ds$ptr, delta_threshold
    ),
    ds,
    "pearson_equivalence"
  )
}

#' @export
print.cir_test <- function(x, ...) {
  cat(sprintf("<cir_test: %s>\n", x$name))
  invisible(x)
}

# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

#' Run a conditional-independence test.
#'
#' @param test A `cir_test` from one of the factory functions.
#' @param x,y Column **names** (length-1 character) for the two variables.
#' @param z Character vector of conditioning column names (default: none).
#' @return A named list `list(statistic, p_value, dof, effect_size)`; absent
#'   fields are `NULL`.
#' @examples
#' df <- data.frame(A = sample(0:1, 80, TRUE), B = sample(0:1, 80, TRUE))
#' run_test(chi_squared(dataset(df)), "A", "B")
#' @export
run_test <- function(test, x, y, z = character()) {
  stopifnot(inherits(test, "cir_test"))
  test$handle$run_test(x, y, .cir_as_names(z))
}

#' Decide conditional independence at a significance level.
#'
#' Applies the test's own decision rule: `p >= significance_level` for the
#' standard tests, and the inverted `p < significance_level` for
#' [pearson_equivalence()].
#'
#' @param test A `cir_test` from one of the factory functions.
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
    significance_level = 0.05) {
  stopifnot(inherits(test, "cir_test"))
  test$handle$is_independent(x, y, .cir_as_names(z), significance_level)
}

#' Normalize a conditioning-set argument to a character vector.
#'
#' Accepts `NULL`, a character vector, or a single name; never a non-character.
#'
#' @param z The `z` argument as supplied by the caller.
#' @return A character vector (possibly empty).
#' @keywords internal
.cir_as_names <- function(z) {
  if (is.null(z)) {
    character()
  } else if (is.character(z)) {
    z
  } else {
    stop("`z` must be a character vector of column names", call. = FALSE)
  }
}
