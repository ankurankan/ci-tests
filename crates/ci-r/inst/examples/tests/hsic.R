library(fastcit)

# Each language makes its own random data, so the values differ from the other tabs.
set.seed(0)
n <- 300
x <- rnorm(n)
y <- x^2 + 0.5 * rnorm(n) # nonlinear dependence, zero correlation
df <- data.frame(X = x, Y = y)

data <- dataset(df)
test <- hsic(data, bandwidth = "median")
res <- run_test(test, "X", "Y")
print(res$statistic)
#> [1] 2668.9
print(res$p_value)
#> [1] 1.728e-40
print(res$dof)
#> NULL
print(res$effect_size)
#> [1] 0.3140
