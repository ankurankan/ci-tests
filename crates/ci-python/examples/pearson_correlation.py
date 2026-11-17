import numpy as np
import fastcit

rng = np.random.default_rng(0)
n = 500
z = rng.standard_normal(n)
x = z + rng.standard_normal(n)  # X and Y depend on Z only
y = z + rng.standard_normal(n)
data = fastcit.Dataset({
    "X": ("continuous", x),
    "Y": ("continuous", y),
    "Z": ("continuous", z),
})

test = fastcit.PearsonCorrelation(data)
result = test.run_test("X", "Y", ["Z"])
print(result.p_value)
