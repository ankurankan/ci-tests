library(fastcit)

# Each language makes its own random data, so the values differ from the other tabs.
set.seed(0)
n <- 500
z <- sample(0:2, n, replace = TRUE)
# X and Y each copy Z about 40% of the time, so they depend on Z only.
x <- ifelse(runif(n) < 0.4, z, sample(0:2, n, replace = TRUE))
y <- ifelse(runif(n) < 0.4, z, sample(0:2, n, replace = TRUE))
df <- data.frame(X = as.integer(x), Y = as.integer(y), Z = as.integer(z))

data <- dataset(df)
test <- freeman_tukey(data)
res <- run_test(test, "X", "Y", "Z")
print(res$statistic)
#> [1] 12.55
print(res$p_value)
#> [1] 0.4024
print(res$dof)
#> [1] 12
print(res$effect_size)
#> [1] 0.1120
