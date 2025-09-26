# Standard Libraries
from dataclasses import dataclass
from typing import Optional, Tuple

# Dependencies
from matplotlib.axes import Axes
from matplotlib.collections import PathCollection


class GeorefSteps:
    def __init__(self):
        self.data = ["target", "base", "saved"]
        self.n = len(self.data)
        self.index = 0

    def __next__(self):
        value = self.data[self.index]
        self.index = (self.index + 1) % self.n
        return value

    def prev(self):
        self.index = (self.index - 1) % self.n
        return self.data[self.index]

    def __iter__(self):
        return self


@dataclass
class GCPString:
    pixel_coords: str
    map_coords: str
    id: str


class GeorefState:
    is_panning: bool = False
    pan_start: Optional[Tuple[float, float]] = None
    pan_ax: Optional[Axes] = None
    georef_steps: GeorefSteps = GeorefSteps()
    georef_current_step: str = ""
    current_gcp: GCPString = GCPString("", "", "")
    gcp_selected: bool = True  # True allows for the first GCP step to occur.
    gcp_count: int = 0


class GeorefPlotObjects:
    def __init__(self, targ_ax: Axes, base_ax: Axes):
        self.targ_point: PathCollection = targ_ax.scatter([], [], color="r")
        self.base_point: PathCollection = base_ax.scatter([], [], color="r")
