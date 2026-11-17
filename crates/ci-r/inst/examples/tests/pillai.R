library(fastcit)

set.seed(0)
n <- 500
z <- sample(0:2, n, replace = TRUE)
x <- z + rnorm(n) # continuous, driven by the discrete Z
y <- z + rnorm(n)
df <- data.frame(X = x, Y = y, Z = as.integer(z))

data <- dataset(df)
test <- pillai(data)
res <- run_test(test, "X", "Y", "Z")
print(res$p_value)
