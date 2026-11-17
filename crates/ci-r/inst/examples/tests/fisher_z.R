library(fastcit)

# Each language makes its own random data, so the values differ from the other tabs.
set.seed(0)
n <- 500
z <- rnorm(n)
x <- z + rnorm(n) # X and Y depend on Z only
y <- z + rnorm(n)
df <- data.frame(X = x, Y = y, Z = z)

data <- dataset(df)
test <- fisher_z(data)
res <- run_test(test, "X", "Y", "Z")
print(res$statistic)
#> [1] -0.1752
print(res$p_value)
#> [1] 0.8609
print(res$dof)
#> NULL
print(res$effect_size)
#> [1] 0.007868
