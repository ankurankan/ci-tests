library(fastcit)

set.seed(0)
n <- 500
z <- sample(0:2, n, replace = TRUE)
# X and Y each copy Z about 40% of the time, so they depend on Z only.
x <- ifelse(runif(n) < 0.4, z, sample(0:2, n, replace = TRUE))
y <- ifelse(runif(n) < 0.4, z, sample(0:2, n, replace = TRUE))
df <- data.frame(X = as.integer(x), Y = as.integer(y), Z = as.integer(z))

data <- dataset(df)
test <- modified_likelihood(data)
res <- run_test(test, "X", "Y", "Z")
print(res$p_value)
