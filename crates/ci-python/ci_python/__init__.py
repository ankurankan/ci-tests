"""Data-bound conditional-independence testing.

Build a :class:`Dataset` once from named, typed columns, then construct any of
the twelve tests bound to that data and query ``run_test`` / ``is_independent``::

    import numpy as np
    from ci_python import Dataset, ChiSquared, PearsonEquivalence

    data = Dataset({
        "A": ("discrete", np.array([0, 1, 0, 1], dtype=float)),
        "B": ("discrete", np.array([1, 1, 0, 0], dtype=float)),
    })
    res = ChiSquared(data).run_test("A", "B")
    res.statistic, res.p_value, res.dof, res.effect_size

The per-test classes are data-bound: they take the :class:`Dataset` (or a raw
``{name: (kind, values)}`` mapping or a :class:`pandas.DataFrame`) plus their
own configuration in the constructor. ``x`` / ``y`` accept a column name or
integer index; ``z`` is a sequence of names/indices.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np

from ci_python._ci_python import (
    GCM,
    HSIC,
    KCI,
    RBF,
    ChiSquared,
    CiError,
    CiResult,
    CressieRead,
    FisherZ,
    FreemanTukey,
    Linear,
    LogLikelihood,
    ModifiedLikelihood,
    PearsonCorrelation,
    PearsonEquivalence,
    PillaiTrace,
)
from ci_python._ci_python import (
    Dataset as _Dataset,
)

if TYPE_CHECKING:  # pragma: no cover - typing-only import
    import pandas as pd
    from numpy.typing import NDArray

__all__ = [
    "GCM",
    "HSIC",
    "KCI",
    "RBF",
    "ChiSquared",
    "CiError",
    "CiResult",
    "CressieRead",
    "Dataset",
    "FisherZ",
    "FreemanTukey",
    "Linear",
    "LogLikelihood",
    "ModifiedLikelihood",
    "PearsonCorrelation",
    "PearsonEquivalence",
    "PillaiTrace",
]


def _safe_issubdtype(dtype: Any, base: Any) -> bool:  # noqa: ANN401
    """Return whether ``dtype`` is a subtype of ``base`` without raising.

    Pandas extension dtypes that NumPy cannot interpret return ``False``.
    """
    try:
        return bool(np.issubdtype(dtype, base))
    except TypeError:
        return False


def _column_from_pandas(series: pd.Series[Any]) -> tuple[str, NDArray[np.float64]]:
    """Infer a column's kind and encode its values for the native dataset.

    Categorical and string/object values become integer codes. Missing values
    remain NaN so the core enforces the same strict missing-data policy.
    """
    import pandas as pd  # noqa: PLC0415 - optional dependency imported lazily

    dtype = series.dtype
    name = str(getattr(dtype, "name", dtype))
    if name == "category":
        codes = np.asarray(series.cat.codes, dtype=np.float64)
        codes[codes == -1.0] = np.nan
        return "discrete", codes
    if name in ("string", "str") or dtype == np.object_ or _safe_issubdtype(dtype, np.str_):
        raw, _ = pd.factorize(series)
        codes = raw.astype(np.float64)
        codes[codes == -1.0] = np.nan
        return "discrete", codes
    # Temporal dtypes are neither categorical nor plain-numeric; reject them
    # explicitly (timedelta64 would otherwise pass the integer check below).
    if _safe_issubdtype(dtype, np.datetime64) or _safe_issubdtype(dtype, np.timedelta64):
        msg = f"cannot infer column kind for temporal dtype {dtype!r}; convert it explicitly first"
        raise TypeError(msg)
    if _safe_issubdtype(dtype, np.floating):
        return "continuous", np.asarray(series, dtype=np.float64)
    if _safe_issubdtype(dtype, np.integer) or _safe_issubdtype(dtype, np.bool_):
        return "discrete", np.asarray(series, dtype=np.float64)
    msg = f"cannot infer column kind for dtype {dtype!r}; pass an explicit mapping"
    raise TypeError(msg)


class Dataset(_Dataset):
    """A named, typed, immutable table shared by the test classes.

    See the native :class:`ci_python._ci_python.Dataset` for the primary
    constructor (a ``{name: (kind, values)}`` mapping). This subclass adds the
    pure-Python :meth:`from_pandas` convenience.
    """

    __slots__ = ()

    @classmethod
    def from_pandas(cls, df: pd.DataFrame) -> Dataset:
        """Build a :class:`Dataset` from a :class:`pandas.DataFrame`.

        Column kinds are inferred from dtypes: integer / boolean / categorical
        / object / string columns become ``"discrete"`` and floating columns
        become ``"continuous"``. Categorical and object/string columns are
        factorized to integer codes; **missing values are mapped to NaN and
        rejected by the core** (strict missing-data policy — drop or impute
        first). ``pandas`` is imported lazily, so it is not a hard dependency
        of this package.

        .. note::
            Passing a :class:`pandas.DataFrame` directly to any test
            constructor (e.g. ``ChiSquared(df)``) is equivalent to
            ``ChiSquared(Dataset.from_pandas(df))`` — a fresh :class:`Dataset`
            is built per constructor call; to share data across tests, build
            a :class:`Dataset` explicitly.
        """
        return cls({str(name): _column_from_pandas(df[name]) for name in df.columns})
