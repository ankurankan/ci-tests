# The generated extendr wrappers expose `Dataset`, `ChiSquared`, ... as
# environments with a `$new()` constructor returning an external pointer. The
# user-facing objects below wrap that pointer together with the ordered column
# names (needed to map pcalg's integer node indices back to names).

#' Infer the column kind ("discrete" or "continuous") for one data.frame column.
#'
#' `double` columns are continuous; everything else
#' (`integer`/`logical`/`factor`/`character`) is discrete.
#'
#' @param col A single data.frame column.
#' @return A scalar string, `"discrete"` or `"continuous"`.
#' @keywords internal
.fastcit_infer_kind <- function(col) {
  if (
    is.factor(col) || is.character(col) || is.logical(col) || is.integer(col)
  ) {
    "discrete"
  } else if (is.double(col)) {
    "continuous"
  } else {
    stop(
      sprintf("unsupported column type: %s", paste(class(col), collapse = "/")),
      call. = FALSE
    )
  }
}

#' Code one data.frame column to a numeric vector for the Rust core.
#'
#' Discrete factor/character/logical columns are mapped to integer codes (the
#' core re-factorizes them anyway, so the exact codes only need to be
#' value-distinct); numeric columns pass through as doubles.
#'
#' @param col A single data.frame column.
#' @return A numeric vector the same length as `col`.
#' @keywords internal
.fastcit_code_column <- function(col) {
  if (is.factor(col)) {
    as.numeric(as.integer(col))
  } else if (is.character(col)) {
    as.numeric(as.integer(factor(col)))
  } else {
    # logical and numeric columns both coerce straight to double.
    as.numeric(col)
  }
}

#' Bind a data.frame as a `fastcit` dataset.
#'
#' Builds the data-bound dataset shared by the test factories. Column kinds are
#' inferred from the column classes (integer/logical/factor/character ->
#' discrete, double -> continuous); discrete factor/character columns are coded
#' to integer codes before reaching the Rust core.
#'
#' Missing values are **rejected**: any `NA` (in a numeric column, a factor,
#' or after coding a character column) reaches the core as NaN and errors with
#' "missing data: ...". Choose a missing-data convention (e.g.
#' `na.omit(df)`) before binding.
#'
#' @param df A data.frame (or object coercible to one).
#' @return An object of class `fastcit_dataset` wrapping the bound dataset and its
#'   column names.
#' @examples
#' df <- data.frame(A = sample(0:1, 50, TRUE), X = rnorm(50))
#' data <- dataset(df)
#' @name fastcit_dataset
#' @export
dataset <- function(df) {
  df <- as.data.frame(df)
  if (ncol(df) == 0L) {
    stop("`df` must have at least one column", call. = FALSE)
  }
  names_vec <- colnames(df)
  kinds <- vapply(df, .fastcit_infer_kind, character(1), USE.NAMES = FALSE)
  coded <- lapply(df, .fastcit_code_column)
  values <- matrix(
    as.numeric(unlist(coded, use.names = FALSE)),
    nrow = nrow(df),
    ncol = ncol(df)
  )
  ptr <- Dataset$new( # nolint: object_usage_linter.
    names_vec, kinds, values
  )
  structure(
    list(ptr = ptr, names = names_vec, kinds = kinds),
    class = "fastcit_dataset"
  )
}

#' @export
print.fastcit_dataset <- function(x, ...) {
  cat(sprintf(
    "<fastcit_dataset: %d columns x %d rows>\n",
    x$ptr$n_cols(), x$ptr$n_rows()
  ))
  cat("  columns:", paste(x$names, collapse = ", "), "\n")
  invisible(x)
}

#' Coerce a `dataset()` result or a data.frame into a `fastcit_dataset`.
#'
#' Lets every test factory accept either a pre-built [dataset()] or a raw
#' data.frame uniformly.
#'
#' @param data A `fastcit_dataset` or a data.frame.
#' @return A `fastcit_dataset`.
#' @keywords internal
.fastcit_as_dataset <- function(data) {
  if (inherits(data, "fastcit_dataset")) {
    data
  } else {
    dataset(data)
  }
}
