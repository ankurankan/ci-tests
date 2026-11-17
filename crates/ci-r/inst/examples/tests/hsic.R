library(fastcit)

set.seed(0)
n <- 300
x <- rnorm(n)
y <- x^2 + 0.5 * rnorm(n) # nonlinear dependence, zero correlation
df <- data.frame(X = x, Y = y)

data <- dataset(df)
test <- hsic(data, bandwidth = "median")
res <- run_test(test, "X", "Y")
print(res$p_value)
