# Standard Libraries
from dataclasses import dataclass
from typing import Optional

# Dependencies
import numpy as np

# Relative Imports
from .custom_types import PathLike


@dataclass
class TargetImage:
    """
    Represents an ungeoreferenced target image and its associated metadata.

    Parameters
    ----------
    data : np.ndarray
        The image data array. Must be 2D (height, width) or 3D
        (bands, height, width).
    row_offset : int, optional
        Number of rows to skip before reading the image window.
        Defaults to 0.
    col_offset : int, optional
        Number of columns to skip before reading the image window.
        Defaults to 0.
    width : int, optional
        Width of the image window. If set to -1 (default), it is inferred
        from the input data array.
    height : int, optional
        Height of the image window. If set to -1 (default), it is inferred
        from the input data array.
    band : int, optional
        The band index to use. If the data array is 2D, this must be 0.
        Defaults to 0.
    src_path : PathLike, optional
        The file path from which the image data was loaded. Useful for
        tracking data provenance.
    """

    data: np.ndarray
    row_offset: int = 0
    col_offset: int = 0
    width: int = -1
    height: int = -1
    band: int = 0
    src_path: Optional[PathLike] = None

    def __post_init__(self):
        if self.data.ndim > 3:
            raise ValueError(
                f"Target Image data has {self.data.ndim}"
                "dimensions, but must have 3 or less."
            )
        if self.data.ndim == 2 and self.band > 0:
            raise ValueError("If the array is 2D, the chosen band must be 0")

        if self.width == -1:
            self.width = self.data.shape[1]
        elif self.width + self.col_offset > self.data.shape[1]:
            raise ValueError(
                f"Window width ({self.width}) is larger "
                f"than the image width: {self.data.shape[1]} "
                f"when the column offset {self.col_offset} is "
                "applied"
            )

        if self.height == -1:
            self.height = self.data.shape[0]
        elif self.height + self.row_offset > self.data.shape[0]:
            raise ValueError(
                f"Window height {self.height} is larger "
                f"than the image height: {self.data.shape[0]} "
                f"when the row offset {self.row_offset} is "
                "applied."
            )


def open_target(target_image: TargetImage) -> np.ndarray:
    """
    Applies row and column offsets to Target Image data attribute and returns
    the resulting array.

    Parameters
    ----------
    target_image: TargetImage
        TargetImage object that will be georeferenced by pixking GCPs.

    Returns
    -------
    arr: np.ndarray
    """
    if target_image.data.ndim == 2:
        target_image.data = target_image.data[:, :, np.newaxis]

    col_off = target_image.col_offset
    row_off = target_image.row_offset
    width = target_image.width
    height = target_image.height

    arr = target_image.data[
        row_off : row_off + height,  # noqa
        col_off : col_off + width,  # noqa
        target_image.band,
    ]

    return arr
