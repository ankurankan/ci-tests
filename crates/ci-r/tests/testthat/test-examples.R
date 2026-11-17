# Every documentation example under inst/examples/tests prints the four fields
# of its result. The `#>` comments right under each print() line show the
# output. These tests run each example and compare its output with those
# comments. A number in a comment matches to the precision written there, as
# with the NUMBER option of pytest doctests: 0.5778 matches 0.577822.

library(fastcit)

# A number with a decimal point or an exponent, as in the NUMBER option of
# pytest doctests. Integers are not numbers here: they match as text.
number_pattern <- paste0(
  "[+-]?(?:[0-9]*[.][0-9]+|[0-9]+[.])(?:[eE][+-]?[0-9]+)?",
  "|[+-]?[0-9]+[eE][+-]?[0-9]+"
)

# One unit in the last written digit of a number: 0.5778 gives 1e-04.
last_digit_unit <- function(number) {
  mantissa <- sub("[eE].*$", "", number)
  exponent <- if (grepl("[eE]", number)) sub("^.*[eE]", "", number) else "0"
  fraction <- if (grepl(".", mantissa, fixed = TRUE)) {
    sub("^.*[.]", "", mantissa)
  } else {
    ""
  }
  10^(as.numeric(exponent) - nchar(fraction))
}

# TRUE when the output line `got` is the shown line `want`. As with pytest's
# NUMBER option, each number of `want` matches to its written precision.
output_matches <- function(want, got) {
  want <- trimws(want, "right")
  got <- trimws(got, "right")
  wants <- regmatches(want, gregexpr(number_pattern, want, perl = TRUE))[[1]]
  gots <- regmatches(got, gregexpr(number_pattern, got, perl = TRUE))[[1]]
  same_text <- identical(
    gsub(number_pattern, "", want, perl = TRUE),
    gsub(number_pattern, "", got, perl = TRUE)
  )
  if (length(wants) != length(gots) || !same_text) {
    return(FALSE)
  }
  got_values <- as.numeric(gots)
  tolerance <- pmax(
    vapply(wants, last_digit_unit, numeric(1L)),
    1e-6 * abs(got_values)
  )
  all(abs(as.numeric(wants) - got_values) <= tolerance)
}

# The shown output: the `#>` comment lines under each print() line, without
# the "#> " mark. A `#>` line that is not under a print() line is an error.
shown_output <- function(lines) {
  shown <- character()
  after_print <- FALSE
  for (line in lines) {
    if (startsWith(line, "#>")) {
      if (!after_print) stop("a #> comment is not under a print() line: ", line)
      shown <- c(shown, sub("^#> ?", "", line))
    } else {
      after_print <- startsWith(line, "print(")
    }
  }
  shown
}

example_dir <- system.file("examples/tests", package = "fastcit")
example_files <- sort(
  list.files(example_dir, pattern = "[.]R$", full.names = TRUE)
)

test_that("all twelve test examples are installed", {
  expect_length(example_files, 12L)
})

fields <- c("statistic", "p_value", "dof", "effect_size")

for (path in example_files) {
  local({
    path <- path
    test_that(paste("example", basename(path), "shows its output"), {
      lines <- readLines(path)
      expect_true(all(sprintf("print(res$%s)", fields) %in% lines))
      shown <- shown_output(lines)
      out <- capture.output(source(path, local = new.env()))
      expect_length(out, length(shown))
      for (i in seq_len(min(length(out), length(shown)))) {
        expect(
          output_matches(shown[[i]], out[[i]]),
          sprintf("shows `%s`, but prints `%s`", shown[[i]], out[[i]])
        )
      }
    })
  })
}

test_that("shown numbers match to the written precision", {
  # 0.5778 is 0.577822 at 4 significant digits. The digits after the 4th do
  # not count, but a wrong digit before them does.
  expect_true(output_matches("[1] 0.5778", "[1] 0.577822"))
  expect_true(output_matches("[1] 0.5778", "[1] 0.577862"))
  expect_false(output_matches("[1] 0.5768", "[1] 0.577822"))
  expect_true(output_matches("[1] 1.716e-42", "[1] 1.715877e-42"))
  expect_false(output_matches("[1] 1.726e-42", "[1] 1.715877e-42"))
  # Integers and other text match exactly.
  expect_true(output_matches("[1] 12", "[1] 12"))
  expect_false(output_matches("[1] 12", "[1] 13"))
  expect_true(output_matches("NULL", "NULL"))
  expect_false(output_matches("NULL", "[1] 0.5778"))
})

test_that("the output comments are the #> lines under a print() line", {
  lines <- c(
    "x <- 1 # a comment",
    "print(x)",
    "#> [1] 1",
    "print(c(a = 1))",
    "#> a",
    "#> 1"
  )
  expect_identical(shown_output(lines), c("[1] 1", "a", "1"))
  expect_error(shown_output(c("x <- 1", "#> [1] 1")), "not under a print")
})
