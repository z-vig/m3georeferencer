# Standard Libraries
from dataclasses import dataclass
from typing import Sequence, Tuple

# Dependencies
import numpy as np
import rasterio as rio  # type: ignore
from rasterio.coords import BoundingBox  # type: ignore
from rasterio.crs import CRS  # type: ignore
from rasterio.windows import Window  # type: ignore

# Relative Imports
from .custom_types import PathLike


@dataclass
class BaseImage:
    path: PathLike
    crs: str | CRS
    bbox: Tuple[float, float, float, float] | BoundingBox
    geotransform: Sequence[float] = (0.0, 1.0, 0.0, 0.0, 0.0, 1.0)

    def __post_init__(self):
        self.bbox = BoundingBox(*self.bbox)
        self.crs = CRS.from_wkt(self.crs)


# Gruithuisen Domes: -41.4, 35.3, -38.9, 37.6
def open_base(base_image: BaseImage) -> Tuple[np.ndarray, Window]:
    """
    Opens data from path attribute of base_image and modifies base_image
    geotransform attribute.

    Parameters
    ----------
    base_image: BaseImage
        BaseImage object to use a basemap for georeferencing. The image must
        already have geospatial information encoded (i.e. A GeoTiff)

    Returns
    -------
    arr: np.ndarray
        Read in data within the bounding box
    window: Window
        Window corresponding to the bounding box. Window is in pixel coords.
    """
    with rio.open(base_image.path) as dst:
        w = dst.window(*base_image.bbox)
        arr = dst.read(indexes=1, window=w)
        base_image.geotransform = dst.transform.to_gdal()
    return (arr, w)
