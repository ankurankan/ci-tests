library(fastcit)

set.seed(1)
n <- 200
z <- rnorm(n)
x <- z^2 + 0.5 * rnorm(n) # nonlinear in Z
y <- z^2 + 0.5 * rnorm(n)
df <- data.frame(X = x, Y = y, Z = z)

data <- dataset(df)
test <- kci(data, bandwidth = "median")
res <- run_test(test, "X", "Y", "Z")
print(res$p_value)
