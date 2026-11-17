import numpy as np
import fastcit

rng = np.random.default_rng(0)
n = 200
z = rng.standard_normal(n)
x = z**2 + 0.5 * rng.standard_normal(n)  # nonlinear in Z
y = z**2 + 0.5 * rng.standard_normal(n)
data = fastcit.Dataset({
    "X": ("continuous", x),
    "Y": ("continuous", y),
    "Z": ("continuous", z),
})

test = fastcit.KCI(data, bandwidth="median")
result = test.run_test("X", "Y", ["Z"])
print(result.p_value)
