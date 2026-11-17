library(fastcit)

set.seed(0)
n <- 2000
z <- rnorm(n)
x <- z + rnorm(n) # X and Y depend on Z only
y <- z + rnorm(n)
df <- data.frame(X = x, Y = y, Z = z)

data <- dataset(df)
# A small p-value supports equivalence: |rho| < threshold,
# so X and Y are independent given Z.
test <- pearson_equivalence(data, delta_threshold = 0.1)
res <- run_test(test, "X", "Y", "Z")
print(res$p_value)
