#' cir: data-bound conditional-independence tests
#'
#' A small, function-style R surface over the Rust core. Bind a data.frame once
#' with [dataset()], construct a test with one of the factory functions
#' ([chi_squared()], [pearson_correlation()], ...), then query it with
#' [run_test()] / [is_independent()]. [as_pcalg()] adapts any test into the
#' `indepTest` callback shape expected by the \pkg{pcalg} package.
#'
#' Column kinds are inferred from the data.frame: `integer`/`logical`/`factor`/
#' `character` columns are treated as **discrete**, `double` columns as
#' **continuous**. Discrete factor/character columns are coded to integer codes
#' on the R side before they reach the Rust core (which only handles numbers).
#'
#' @keywords internal
"_PACKAGE"
