library(fastcit)

# Each language makes its own random data, so the values differ from the other tabs.
set.seed(1)
n <- 200
z <- rnorm(n)
x <- z^2 + 0.5 * rnorm(n) # nonlinear in Z
y <- z^2 + 0.5 * rnorm(n)
df <- data.frame(X = x, Y = y, Z = z)

data <- dataset(df)
test <- kci(data, bandwidth = "median")
res <- run_test(test, "X", "Y", "Z")
print(res$statistic)
#> [1] 14.52
print(res$p_value)
#> [1] 0.4581
print(res$dof)
#> NULL
print(res$effect_size)
#> [1] 0.01943
