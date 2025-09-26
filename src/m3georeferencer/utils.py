# Standard Libraries
from typing import Sequence, Tuple

# Dependencies
from matplotlib.axes import Axes


def forward_geotransform(
    x_pixel: float, y_pixel: float, geotrans: Sequence[float]
) -> Tuple[float, float]:
    """Converts from pixel coordinates to map coordinates"""
    origin_x, pixel_width, _, origin_y, _, pixel_height = geotrans
    x_geo = origin_x + x_pixel * pixel_width
    y_geo = origin_y + y_pixel * pixel_height
    return (x_geo, y_geo)


def color_axis(ax: Axes, color: str) -> None:
    for spine in ax.spines.values():
        spine.set_edgecolor(color)
        spine.set_linewidth(2)


def set_image_axis(ax: Axes) -> None:
    ax.set_xticks([])
    ax.set_yticks([])
    ax.tick_params(
        axis="both",
        which="both",
        bottom=False,
        top=False,
        left=False,
        right=False,
        labelbottom=False,
        labelleft=False,
    )
    color_axis(ax, "k")
