import numpy as np
import fastcit

rng = np.random.default_rng(0)
n = 300
x = rng.standard_normal(n)
y = x**2 + 0.5 * rng.standard_normal(n)  # nonlinear dependence, zero correlation
data = fastcit.Dataset({"X": ("continuous", x), "Y": ("continuous", y)})

test = fastcit.HSIC(data, bandwidth="median")
result = test.run_test("X", "Y")
print(result.p_value)
