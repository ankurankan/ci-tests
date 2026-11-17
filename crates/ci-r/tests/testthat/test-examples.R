# Every documentation example under inst/examples/tests must run and print a
# p-value in [0, 1].

library(fastcit)

example_dir <- system.file("examples/tests", package = "fastcit")
example_files <- sort(
  list.files(example_dir, pattern = "[.]R$", full.names = TRUE)
)

test_that("all twelve test examples are installed", {
  expect_length(example_files, 12L)
})

for (path in example_files) {
  local({
    path <- path
    test_that(paste("example", basename(path), "prints a p-value"), {
      out <- capture.output(source(path, local = new.env()))
      value <- as.numeric(sub("^\\[1\\]\\s+", "", out[nzchar(out)]))
      expect_length(value, 1L)
      expect_true(value >= 0 && value <= 1)
      key <- sub("[.]R$", "", basename(path))
      # hsic: dependent data; pearson_equivalence: a small p-value supports
      # equivalence; all others: conditionally independent data.
      if (key == "hsic") {
        expect_lt(value, 0.001)
      } else if (key == "pearson_equivalence") {
        expect_lt(value, 0.05)
      } else {
        expect_gt(value, 0.05)
      }
    })
  })
}
