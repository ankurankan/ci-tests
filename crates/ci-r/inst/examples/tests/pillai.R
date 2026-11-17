library(fastcit)

# Each language makes its own random data, so the values differ from the other tabs.
set.seed(0)
n <- 500
z <- sample(0:2, n, replace = TRUE)
x <- z + rnorm(n) # continuous, driven by the discrete Z
y <- z + rnorm(n)
df <- data.frame(X = x, Y = y, Z = as.integer(z))

data <- dataset(df)
test <- pillai(data)
res <- run_test(test, "X", "Y", "Z")
print(res$statistic)
#> [1] 0.005013
print(res$p_value)
#> [1] 0.1138
print(res$dof)
#> NULL
print(res$effect_size)
#> [1] 0.005013
