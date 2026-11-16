# Type stubs for the native `fastcit._fastcit` extension module.
# Hand-maintained to match `crates/ci-python/src/lib.rs`.
# ruff: noqa: D101, D102, D107, PYI021, ANN401

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    import pandas as pd

ColumnRef = str | int
ColumnSpec = tuple[str, Any]

class CiError(Exception): ...

class RBF:
    def __init__(self, length_scale: float) -> None: ...
    @property
    def length_scale(self) -> float: ...

class Linear:
    def __init__(self) -> None: ...

_Kernel = RBF | Linear
_KernelSpec = _Kernel | dict[str, _Kernel] | None

class CiResult:
    @property
    def statistic(self) -> float | None: ...
    @property
    def p_value(self) -> float: ...
    @property
    def dof(self) -> int | None: ...
    @property
    def effect_size(self) -> float | None: ...

class Dataset:
    def __init__(self, columns: dict[str, ColumnSpec]) -> None: ...
    @property
    def n_rows(self) -> int: ...
    @property
    def n_cols(self) -> int: ...
    def index_of(self, name: str) -> int: ...

_DatasetInput = Dataset | dict[str, ColumnSpec] | pd.DataFrame

class _BaseTest:
    def run_test(
        self,
        x: ColumnRef,
        y: ColumnRef,
        z: Sequence[ColumnRef] | None = ...,
    ) -> CiResult: ...
    def is_independent(
        self,
        x: ColumnRef,
        y: ColumnRef,
        z: Sequence[ColumnRef] | None = ...,
        significance_level: float = ...,
    ) -> bool: ...
    def meta(self) -> dict[str, Any]: ...

class ChiSquared(_BaseTest):
    def __init__(self, data: _DatasetInput, yates: bool = ...) -> None: ...

class LogLikelihood(_BaseTest):
    def __init__(self, data: _DatasetInput, yates: bool = ...) -> None: ...

class CressieRead(_BaseTest):
    def __init__(self, data: _DatasetInput, yates: bool = ...) -> None: ...

class FisherZ(_BaseTest):
    def __init__(self, data: _DatasetInput) -> None: ...

class GCM(_BaseTest):
    def __init__(self, data: _DatasetInput) -> None: ...

class PillaiTrace(_BaseTest):
    def __init__(self, data: _DatasetInput) -> None: ...

class FreemanTukey(_BaseTest):
    def __init__(self, data: _DatasetInput, yates: bool = ...) -> None: ...

class ModifiedLikelihood(_BaseTest):
    def __init__(self, data: _DatasetInput, yates: bool = ...) -> None: ...

class PearsonCorrelation(_BaseTest):
    def __init__(self, data: _DatasetInput) -> None: ...

class PearsonEquivalence(_BaseTest):
    def __init__(
        self,
        data: _DatasetInput,
        delta_threshold: float = ...,
    ) -> None: ...

class HSIC(_BaseTest):
    def __init__(
        self,
        data: _DatasetInput,
        kernel: _KernelSpec = ...,
        bandwidth: Literal["heuristic", "median"] = ...,
        null_dist: Literal["gamma", "permutation"] = ...,
        n_permutations: int = ...,
        seed: int = ...,
    ) -> None: ...

class KCI(_BaseTest):
    def __init__(
        self,
        data: _DatasetInput,
        kernel: _KernelSpec = ...,
        bandwidth: Literal["heuristic", "median"] = ...,
        epsilon: float = ...,
    ) -> None: ...
