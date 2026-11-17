import numpy as np
import fastcit

rng = np.random.default_rng(0)
n = 500
z = rng.integers(0, 3, n)
x = z + rng.standard_normal(n)  # continuous, driven by the discrete Z
y = z + rng.standard_normal(n)
data = fastcit.Dataset({
    "X": ("continuous", x),
    "Y": ("continuous", y),
    "Z": ("discrete", z.astype(float)),
})

test = fastcit.PillaiTrace(data)
result = test.run_test("X", "Y", ["Z"])
print(result.p_value)
