# Standard Libraries
from pathlib import Path
from uuid import uuid4

# Dependencies
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import RangeSlider


# Relative Imports
from .custom_types import PathLike
from .target_image import TargetImage, open_target
from .base_image import BaseImage, open_base
from .georeferencer_classes import GeorefPlotObjects, GeorefState
from .utils import set_image_axis, forward_geotransform, color_axis


class Georeferencer:
    """
    Opens a georeferencing GUI when an instance is made.

    Parameters
    ----------
    target_image: TargetImage
        Ungeoreferenced image.
    base_image: BaseImage
        Georeferenced image to use as the basemap.
    save_path: PathLike
        Path to save GCPs.
    overwrite_save: bool, optional
        If False (default), an error will be raised if the save_path already
        exists.
    """

    def __init__(
        self,
        target_image: TargetImage,
        base_image: BaseImage,
        save_path: PathLike,
        overwrite_save: bool = False,
        **mpl_kwargs,
    ):
        self.targ = open_target(target_image)
        self.base, self.base_window = open_base(base_image)
        self.transform = base_image.geotransform
        self.save_path = Path(save_path).with_suffix(".gcps")
        if self.save_path.is_file() and not overwrite_save:
            raise FileExistsError(
                f"{self.save_path} already exists. If you "
                "want to overwrite these GCPs, set"
                "overwrite_save=True"
            )
        with open(self.save_path, "w") as f:
            f.write(f"Source for Target Image: {target_image.src_path}\n")
            f.write(f"Row Offset: {target_image.row_offset}\n")
            f.write(f"Column Offset: {target_image.col_offset}\n")
            f.write(f"Target Image Height: {target_image.height}\n")
            f.write(f"Target Image Width: {target_image.width}\n")
            f.write(f"Target Image Band Used: {target_image.band}\n")
            f.write("index, pixel_row, pixel_col, map_x, map_y, ID\n")

        self.main_fig = plt.figure(figsize=(8, 10))
        self.main_fig.suptitle("Press Right to begin Georeferencing...")
        gpsc = self.main_fig.add_gridspec(nrows=7, ncols=12)
        self.targ_ax = self.main_fig.add_subplot(gpsc[0:6, 0:6])
        self.base_ax = self.main_fig.add_subplot(gpsc[0:6, 6:12])
        self.targ_slider_ax = self.main_fig.add_subplot(gpsc[6:7, 0:6])
        self.base_slider_ax = self.main_fig.add_subplot(gpsc[6:7, 6:12])
        # Shrink the height of the slider axes
        for ax in [self.targ_slider_ax, self.base_slider_ax]:
            box = ax.get_position()
            ax.set_position(
                (
                    box.x0 + 0.15 * box.width,  # x (move right slightly)
                    box.y0 + 0.15 * box.height,  # y (move up slightly)
                    0.7 * box.width,  # width
                    0.2 * box.height,  # height (shrink)
                )
            )
            ax.set_facecolor("none")  # Make background transparent

        self.targ_ax.set_box_aspect(1)
        self.base_ax.set_box_aspect(1)

        set_image_axis(self.targ_ax)
        set_image_axis(self.base_ax)

        default_mpl = {"cmap": "Grays_r"}
        mpl_kwargs = {**default_mpl, **mpl_kwargs}
        self.targ_display = self.targ_ax.imshow(self.targ, **mpl_kwargs)
        self.base_display = self.base_ax.imshow(self.base, **mpl_kwargs)

        finite_targ = self.targ[np.isfinite(self.targ)]
        self.targ_slider = RangeSlider(
            ax=self.targ_slider_ax,
            label="",
            valmin=finite_targ.min(),
            valmax=finite_targ.max(),
            valinit=(
                float(np.quantile(finite_targ, 0.05)),
                float(np.quantile(finite_targ, 0.95)),
            ),
        )
        self.targ_slider.on_changed(self.update)

        finite_base = self.base[np.isfinite(self.base)]
        self.base_slider = RangeSlider(
            ax=self.base_slider_ax,
            label="",
            valmin=finite_base.min(),
            valmax=finite_base.max(),
            valinit=(
                float(np.quantile(finite_base, 0.05)),
                float(np.quantile(finite_base, 0.95)),
            ),
        )
        self.base_slider.on_changed(self.update)

        self._state = GeorefState()
        self._plotted = GeorefPlotObjects(self.targ_ax, self.base_ax)

        self.main_fig.canvas.mpl_connect("scroll_event", self.on_scroll)
        self.main_fig.canvas.mpl_connect(
            "button_press_event", self.on_button_press
        )
        self.main_fig.canvas.mpl_connect(
            "button_release_event", self.on_release
        )
        self.main_fig.canvas.mpl_connect("motion_notify_event", self.on_motion)
        self.main_fig.canvas.mpl_connect("key_press_event", self.on_key_press)

    def update(self, val):
        self.targ_display.set_clim(*self.targ_slider.val)
        self.base_display.set_clim(*self.base_slider.val)

    def on_scroll(self, event):
        zoom_step = 1.3

        ax = event.inaxes
        if ax == self.targ_ax:
            img = self.targ
        elif ax == self.base_ax:
            img = self.base
        else:
            return

        cur_xlim = ax.get_xlim()
        cur_ylim = ax.get_ylim()

        xdata = event.xdata
        ydata = event.ydata

        x_left = xdata - cur_xlim[0]
        x_right = cur_xlim[1] - xdata
        y_bottom = ydata - cur_ylim[0]
        y_top = cur_ylim[1] - ydata

        if event.button == "up":
            scale = 1 / zoom_step
        elif event.button == "down":
            scale = zoom_step
        else:
            return

        new_xlim = [xdata - x_left * scale, xdata + x_right * scale]
        new_ylim = [ydata - y_bottom * scale, ydata + y_top * scale]

        # Clamp to image bounds
        new_xlim[0] = max(0, new_xlim[0])
        new_xlim[1] = min(img.shape[1], new_xlim[1])
        new_ylim[0] = max(0, new_ylim[0])
        new_ylim[1] = min(img.shape[0], new_ylim[1])

        ax.set_xlim(new_xlim)
        ax.set_ylim(new_ylim)
        self.main_fig.canvas.draw_idle()

    def on_button_press(self, event):
        if event.button == 2 and event.inaxes in [self.targ_ax, self.base_ax]:
            self._state.is_panning = True
            self._state.pan_start = (event.x, event.y)
            self._state.pan_ax = event.inaxes

        if event.button == 1:
            if self._state.georef_current_step == "target":
                if event.inaxes == self.targ_ax:
                    self._plotted.targ_point.set_offsets(
                        [event.xdata, event.ydata]
                    )
                    self._state.current_gcp.pixel_coords = (
                        f"{self._state.gcp_count}, {event.ydata}, "
                        f"{event.xdata}"
                    )
                    self._state.gcp_selected = True
            elif self._state.georef_current_step == "base":
                if event.inaxes == self.base_ax:
                    self._plotted.base_point.set_offsets(
                        [event.xdata, event.ydata]
                    )
                    base_row = event.xdata + self.base_window.col_off
                    base_col = event.ydata + self.base_window.row_off
                    x_geo, y_geo = forward_geotransform(
                        base_row, base_col, self.transform
                    )
                    self._state.current_gcp.map_coords = f"{x_geo}, {y_geo}"
                    self._state.gcp_selected = True
            elif self._state.georef_current_step == "saved":
                pass
        self.main_fig.canvas.draw_idle()

    def on_release(self, event):
        if event.button == 2:
            self._state.is_panning = False
            self._state.pan_start = None
            self._state.pan_ax = None

    def on_motion(self, event):
        sensitivity = 0.2
        if not self._state.is_panning:
            return
        if self._state.pan_start is None or self._state.pan_ax is None:
            return
        if event.inaxes != self._state.pan_ax:
            return
        if event.x is None or event.y is None:
            return

        ax = self._state.pan_ax
        inv = ax.transData.inverted()

        start_pt = inv.transform(self._state.pan_start)
        end_pt = inv.transform((event.x, event.y))

        dx_data = (start_pt[0] - end_pt[0]) * sensitivity
        dy_data = (start_pt[1] - end_pt[1]) * sensitivity

        cur_xlim = ax.get_xlim()
        cur_ylim = ax.get_ylim()

        ax.set_xlim(cur_xlim[0] + dx_data, cur_xlim[1] + dx_data)
        ax.set_ylim(cur_ylim[0] + dy_data, cur_ylim[1] + dy_data)

        self._pan_start = (event.x, event.y)
        self.main_fig.canvas.draw_idle()

    def on_key_press(self, event):
        if event.key == "right":
            if self._state.gcp_selected:
                self._state.georef_current_step = next(
                    self._state.georef_steps
                )
                self._state.gcp_selected = False

        if self._state.georef_current_step == "target":
            color_axis(self.targ_ax, "red")
        if self._state.georef_current_step == "base":
            color_axis(self.targ_ax, "k")
            color_axis(self.base_ax, "red")
        if self._state.georef_current_step == "saved":
            color_axis(self.base_ax, "k")

            self._state.gcp_selected = True
            self._state.gcp_count += 1
            self._state.current_gcp.id = str(uuid4())

            self._plotted = GeorefPlotObjects(self.targ_ax, self.base_ax)

            with open(self.save_path, "a") as f:
                for i in vars(self._state.current_gcp):
                    f.write(f"{getattr(self._state.current_gcp, i)}, ")
                f.write("\n")

        # else:
        #     self.targ_ax.set_title("")
        #     color_axis(self.targ_ax, "k")
        #     color_axis(self.base_ax, "k")

        self.main_fig.canvas.draw_idle()
