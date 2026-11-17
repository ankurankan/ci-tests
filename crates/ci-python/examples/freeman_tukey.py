import numpy as np
import fastcit

rng = np.random.default_rng(0)
n = 500
z = rng.integers(0, 3, n)
# X and Y each copy Z about 40% of the time, so they depend on Z only.
x = np.where(rng.random(n) < 0.4, z, rng.integers(0, 3, n))
y = np.where(rng.random(n) < 0.4, z, rng.integers(0, 3, n))
data = fastcit.Dataset({
    "X": ("discrete", x.astype(float)),
    "Y": ("discrete", y.astype(float)),
    "Z": ("discrete", z.astype(float)),
})

test = fastcit.FreemanTukey(data)
result = test.run_test("X", "Y", ["Z"])
print(result.p_value)
