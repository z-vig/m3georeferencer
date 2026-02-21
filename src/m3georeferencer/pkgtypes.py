from enum import Enum, auto
from typing_extensions import Self


_order = ["IDLE", "TARGETSELECT", "BASEMAPSELECT"]


class AppMode(Enum):
    IDLE = auto()
    TARGETSELECT = auto()
    BASEMAPSELECT = auto()

    def next(self) -> Self:
        idx = _order.index(self.name)
        next_idx = (idx + 1) % len(_order)
        return type(self)[_order[next_idx]]
