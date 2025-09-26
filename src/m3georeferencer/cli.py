# Standard Libraries
from tkinter.filedialog import asksaveasfilename

# Dependencies
import arguably
import matplotlib.pyplot as plt
import matplotlib

# Relative Imports
from .read_m3 import read_m3
from .target_image import TargetImage
from .base_image import BaseImage

from .georeferencer import Georeferencer

matplotlib.use("QtAgg")


@arguably.command
def georef(
    data: str,
    hdr: str,
    *,
    basemap: str = "./basemap.tif",
    left_bound: float = -22.1,
    right_bound: float = -3.4,
    bottom_bound: float = 4.8,
    top_bound: float = 14.9,
    row_offset: int = 0,
    col_offset: int = 0,
    width: int = 304,
    height: int = 1000,
):
    """
    Show the value of some args.
    Args:
        data: File path of the M3 data file to be georeferenced.
        basemap: [-B] File path to the global WAC basemap.
        left_bound: [-l] Left edge longitude of the bounding box.
        right_bound: [-r] Right edge longitude of the bounding box.
        bottom_bound: [-b] Bottom edge latitude of the bounding box.
        top_bound: [-t] Top edge of latitude of the bounding box.
        row_offset: [-R] Number of rows to offset the M3 Image by in the
                    visualizer.
        col_offset: [-C] Number of columns to offset the M3 Image by in the
                    visualizer.
        width: [-W] Width of the M3 image in the visualizer.
        height: [-H] Height of the M3 image in the visualizer.
    """
    m3_arr = read_m3(data, hdr)
    print(f"Using an M3 image of size: {m3_arr.shape}")
    target = TargetImage(
        m3_arr, row_offset, col_offset, width, height, src_path=data
    )
    base = BaseImage(
        basemap,
        'GEOGCS["GCS_Moon_2000",DATUM["D_Moon_2000",SPHEROID'
        '["Moon_2000_IAU_IAG",1737400.0,0.0]],PRIMEM'
        '["Reference_Meridian",0.0],UNIT["Degree",0.0174532925199433]]',
        (left_bound, bottom_bound, right_bound, top_bound),
    )

    save_path = asksaveasfilename(
        title="Select location to save Ground Control Points.",
        filetypes=[("gcps", ".gcps")],
    )
    Georeferencer(target, base, save_path, overwrite_save=True)
    plt.show()


def main():
    arguably.run()
