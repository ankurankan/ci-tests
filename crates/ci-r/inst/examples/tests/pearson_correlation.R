library(fastcit)

set.seed(0)
n <- 500
z <- rnorm(n)
x <- z + rnorm(n) # X and Y depend on Z only
y <- z + rnorm(n)
df <- data.frame(X = x, Y = y, Z = z)

data <- dataset(df)
test <- pearson_correlation(data)
res <- run_test(test, "X", "Y", "Z")
print(res$p_value)
