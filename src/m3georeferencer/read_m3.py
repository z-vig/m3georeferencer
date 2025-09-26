# Standard Libraries
from dataclasses import dataclass
from pathlib import Path
import os
from typing import Tuple, Mapping
import re

# Top-Level Imports
# from m3py.formats.m3_data_format import M3DataFormat

# Dependencies
import numpy as np

type pathlike = str | os.PathLike


@dataclass
class Window:
    """
    Class for keeping track of window information for image viewing.
    The user will specify the bottom left row (X) and column (Y) of the window
    as well as the width and height as shown below:
    """

    X: int
    Y: int
    W: int
    H: int


dtype_dict: Mapping[int, Tuple[type, int]] = {
    5: (np.float64, 64 // 8),
    4: (np.float32, 32 // 8),
    2: (np.int16, 16 // 8),
}


def read_m3(
    img_path: str | os.PathLike,
    hdr_path: str | os.PathLike,
    x: int = 0,
    y: int = 0,
    w: int | None = None,
    h: int | None = None,
):
    with open(hdr_path) as f:
        fread = f.read()
        nbands = int(re.findall(re.compile(r"bands\s=\s*(\d+)"), fread)[0])
        ncols = int(re.findall(re.compile(r"samples\s=\s*(\d+)"), fread)[0])
        nlines = int(re.findall(re.compile(r"lines\s=\s*(\d+)"), fread)[0])
        dtype, nbytes = dtype_dict.get(
            int(re.findall(re.compile(r"data\stype\s=\s*(\d+)"), fread)[0]),
            (None, None),
        )
        hdrlen_find = re.findall(
            re.compile(r"\s*major\sframe\soffsets\s=\s\{(\d+),\s\d\}"),
            fread,
        )

        if len(hdrlen_find) == 0:
            hdrlen = 0
        else:
            hdrlen = int(hdrlen_find[0])

    img_path = Path(img_path)
    if w is None or h is None:
        w = ncols
        h = nlines
    window = Window(X=x, Y=y, W=w, H=h)
    if (dtype is None) or (nbytes is None):
        raise ValueError(f"{dtype} is an invalid data type.")

    full_col_bytes = hdrlen + (ncols * nbands * nbytes)

    total_rows = os.path.getsize(img_path) // full_col_bytes

    if window is None:
        window = Window(0, 0, ncols, total_rows)

    start_row = window.Y
    col_offset = hdrlen + (window.X * nbands * nbytes)
    start_byte = start_row * full_col_bytes
    col_end_buffer = (ncols - (window.X + window.W)) * nbytes

    # Validating Window
    xbounds_chk = (window.Y + window.H) > total_rows
    ybounds_chk = (window.X + window.W) > ncols
    if xbounds_chk and not ybounds_chk:
        raise ValueError("Window does not fit within X bounds.")
    elif ybounds_chk and not xbounds_chk:
        raise ValueError("Window does not fit within Y bounds.")
    elif xbounds_chk and ybounds_chk:
        raise ValueError("Window does not fit within either X or Y bounds.")

    window_data: np.ndarray = np.empty(
        [window.H, window.W, nbands], dtype=dtype
    )

    with open(img_path, "rb") as f:
        byte_index = 0
        f.seek(start_byte)
        byte_index = f.tell()
        for i in range(0, window.H):
            f.seek(col_offset + byte_index)
            for j in range(0, nbands):
                bindat = f.read(window.W * nbytes)
                byte_index = f.tell()
                f.seek(byte_index + col_end_buffer)
                row: np.ndarray = np.frombuffer(bindat, dtype=dtype)
                window_data[i, :, j] = row
                byte_index = f.tell()

    if window_data.shape[1] == 320:
        window_data = window_data[:, ::-1, :]

    return window_data


if __name__ == "__main__":
    import matplotlib.pyplot as plt

    arr = read_m3(
        "D:/moon_data/m3/Gambart_A_region/M3G20090110T154845/pds_data/L1/M3G20090110T154845_V03_RDN.IMG",  # noqa
        "D:/moon_data/m3/Gambart_A_region/M3G20090110T154845/pds_data/L1/M3G20090110T154845_V03_RDN.HDR",  # noqa
        0,
        0,
        304,
        11000,
    )

    plt.imshow(arr[:, :, 0], cmap="Grays_r")
    plt.show()
