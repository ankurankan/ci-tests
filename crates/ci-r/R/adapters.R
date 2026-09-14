#' Adapt a `cir_test` into a \pkg{pcalg} `indepTest` callback.
#'
#' Returns a closure `function(x, y, S, suffStat)` matching the interface
#' [pcalg::pc()] / [pcalg::skeleton()] expect: `x` and `y` are **1-based**
#' integer node indices, `S` is an integer vector of conditioning node indices
#' (possibly empty), and the return value is the test's p-value. The node
#' indices are mapped back to the bound dataset's column names in their bound
#' order, so pass `labels = colnames(df)` (in the same order) to the pcalg
#' driver. `suffStat` is accepted for interface compatibility and ignored (the
#' data is already captured in `test`); pass `suffStat = list()`.
#'
#' @param test A `cir_test` from one of the factory functions. Must be a
#'   standard null-of-independence test; [pearson_equivalence()] is rejected
#'   because its inverted decision rule (independence when `p < alpha`) would be
#'   interpreted backwards by \pkg{pcalg}.
#' @return A function `(x, y, S, suffStat) -> numeric` p-value.
#' @examples
#' \dontrun{
#' df <- data.frame(X = rnorm(200), Y = rnorm(200), Z = rnorm(200))
#' indepTest <- as_pcalg(pearson_correlation(dataset(df)))
#' pcalg::pc(suffStat = list(), indepTest = indepTest,
#'           labels = colnames(df), alpha = 0.05)
#' }
#' @export
as_pcalg <- function(test) {
  stopifnot(inherits(test, "cir_test"))
  # pcalg interprets the returned p-value with the standard convention: remove
  # an edge / declare independence when p >= alpha. A test whose own rule is
  # inverted -- independence when p < alpha, i.e. the core's
  # `IndependenceRule::PValueLt` -- would have every decision silently flipped,
  # yielding a wrong skeleton/CPDAG with no error. Refuse them.
  if (test$handle$decision_rule() == "p_value_lt") {
    stop(sprintf(
      paste0(
        "as_pcalg() supports only standard null-of-independence tests; `%s` ",
        "uses an inverted decision rule (independence when p < alpha), which ",
        "pcalg would interpret backwards and silently invert every edge ",
        "decision. Use a standard test such as fisher_z() or ",
        "pearson_correlation() for constraint-based discovery."
      ),
      test$name
    ), call. = FALSE)
  }
  cols <- test$dataset$names
  handle <- test$handle
  function(x, y, S, suffStat) { # nolint: object_name_linter.
    xi <- cols[[x]]
    yi <- cols[[y]]
    zi <- if (length(S) > 0L) cols[as.integer(S)] else character()
    res <- handle$run_test(xi, yi, zi)
    res$p_value
  }
}

# ---------------------------------------------------------------------------
# Optional base-R `htest` adapter
# ---------------------------------------------------------------------------

#' Run a test and return a base-R `htest` object.
#'
#' A convenience wrapper for base-R / \pkg{bnlearn}-style workflows: the result
#' carries the `statistic` and the `parameter` (degrees of freedom) alongside
#' the `p.value`.
#'
#' @param test A `cir_test` from one of the factory functions.
#' @param x,y Column names for the two variables.
#' @param z Character vector of conditioning column names (default: none).
#' @return An object of class `htest`.
#' @export
ci_test <- function(test, x, y, z = character()) {
  stopifnot(inherits(test, "cir_test"))
  res <- run_test(test, x, y, z)

  statistic <- res$statistic
  if (!is.null(statistic)) {
    names(statistic) <- "statistic"
  }
  parameter <- res$dof
  if (!is.null(parameter)) {
    parameter <- as.numeric(parameter)
    names(parameter) <- "df"
  }

  znames <- .cir_as_names(z)
  zlab <- if (length(znames) > 0L) {
    paste0(" | ", paste(znames, collapse = ", "))
  } else {
    ""
  }

  structure(
    list(
      statistic = statistic,
      parameter = parameter,
      p.value = res$p_value,
      estimate = if (is.null(res$effect_size)) {
        NULL
      } else {
        c(effect_size = res$effect_size)
      },
      method = sprintf("cir %s conditional independence test", test$name),
      data.name = sprintf("%s vs %s%s", x, y, zlab)
    ),
    class = "htest"
  )
}
