from PySide6.QtCore import Qt, QObject, Slot, Signal
from PySide6.QtGui import QKeyEvent

import pyqtgraph as pg  # type: ignore
from pyqtgraph.graphicsItems.ScatterPlotItem import (  # type: ignore
    ScatterPlotItem,
)
import cmap

from m3georeferencer.ui.widgets.clickable_image import ClickableImage
from m3georeferencer.services.data_transfer_classes import (
    ImageClickData,
    ImageScatterPoint,
)
from m3georeferencer.interaction_filters import is_regular_left_click
from m3georeferencer.global_state import AppState
from m3georeferencer.services.gcp_model import Point, ImageOffset
from m3georeferencer.services.geotransform import GeotransformModel


class AbstractImageController(QObject):
    key_pressed = Signal(QKeyEvent)

    def __init__(self, state: AppState) -> None:
        super().__init__()
        self._img: ClickableImage | None = None
        self._state = state
        self.active: bool = False
        self.current_point: Point = Point(x=0, y=0)
        self.current_scatter: ImageScatterPoint = ImageScatterPoint.empty()
        self.current_scatter.scatter_plot_item.setVisible(False)

        self.pt_cache: list[ImageScatterPoint] = []

    @property
    def img(self) -> ClickableImage:
        if self._img is None:
            raise ValueError("No Basemap Set.")
        return self._img

    def _connect_signals(self) -> None:
        if self._img is None:
            return
        self._img.key_pressed.connect(self.on_key_press)
        self._img.pixel_clicked.connect(self.on_click)

    @Slot(QKeyEvent)
    def on_key_press(self, event: QKeyEvent) -> None:
        if event.key() != Qt.Key.Key_Right:
            return
        self.key_pressed.emit(event)

    @Slot(ImageClickData)
    def on_click(self, data: ImageClickData) -> None:
        if not self.active:
            return
        if not is_regular_left_click(data):
            return
        self.img._vbox.removeItem(self.current_scatter.scatter_plot_item)
        c = cmap.Color("red")
        scatter = pg.ScatterPlotItem(
            x=[data.x_exact],
            y=[data.y_exact],
            brush=pg.mkBrush(c.hex),
            size=10,
        )
        self.img._vbox.addItem(scatter)
        self.current_scatter = ImageScatterPoint(
            data.x_exact, data.y_exact, c, scatter
        )

    def cache_current(self) -> None:
        self.pt_cache.append(self.current_scatter)
        self.img._vbox.addItem(self.current_scatter.copy_scatter_plot_item())

    def sync_with_gcp_group(self) -> None:
        for i in self.img._vbox.addedItems:
            if isinstance(i, ScatterPlotItem):
                self.img._vbox.removeItem(i)


class BasemapImageController(AbstractImageController):
    def __init__(self, state: AppState) -> None:
        super().__init__(state)
        self._geotransform: GeotransformModel | None = None

    @property
    def geotransform(self) -> GeotransformModel:
        if self._geotransform is None:
            raise ValueError("Geotransform is not set.")
        return self._geotransform

    @geotransform.setter
    def geotransform(self, value: GeotransformModel) -> None:
        self._geotransform = value

    def set_img(
        self, value: ClickableImage, gtrans: GeotransformModel
    ) -> None:
        self._img = value
        self._geotransform = gtrans
        self._connect_signals()
        self.img._vbox.addItem(self.current_scatter.scatter_plot_item)

    def _connect_signals(self):
        super()._connect_signals()
        if self._img is None:
            return

    @Slot(ImageClickData)
    def on_click(self, data: ImageClickData) -> None:
        super().on_click(data)
        if is_regular_left_click(data) and self.active:
            map_point = self.geotransform.pixel_to_map(
                xpixel=data.x_exact, ypixel=data.y_exact
            )
            self.current_point = Point(x=map_point.x, y=map_point.y)

    def sync_with_gcp_group(self) -> None:
        super().sync_with_gcp_group()
        for gcp in self._state.gcp_group.gcp_list:
            pt = self.geotransform.map_to_pixel(gcp.map_x, gcp.map_y)
            scatter = pg.ScatterPlotItem(
                x=[pt.x], y=[pt.y], brush=pg.mkBrush("red")
            )
            self.img._vbox.addItem(scatter)


class TargetImageController(AbstractImageController):
    def __init__(self, state: AppState) -> None:
        super().__init__(state)
        self._offset: ImageOffset | None = None

    @property
    def offset(self) -> ImageOffset:
        if self._offset is None:
            raise ValueError("Geotransform is not set.")
        return self._offset

    @offset.setter
    def offset(self, value: ImageOffset) -> None:
        self._offset = value

    def set_img(self, value: ClickableImage, offset: ImageOffset) -> None:
        self._img = value
        self._offset = offset
        self._connect_signals()

    def _connect_signals(self):
        super()._connect_signals()
        if self._img is None:
            return
        self._img.pixel_clicked.connect(self.on_click)

    @Slot(ImageClickData)
    def on_click(self, data: ImageClickData) -> None:
        super().on_click(data)
        if is_regular_left_click(data) and self.active:
            self.current_point = Point(x=data.x_exact, y=data.y_exact)

    def sync_with_gcp_group(self) -> None:
        super().sync_with_gcp_group()
        for gcp in self._state.gcp_group.gcp_list:
            scatter = pg.ScatterPlotItem(
                x=[gcp.pixel_column],
                y=[gcp.pixel_row],
                brush=pg.mkBrush("red"),
            )
            self.img._vbox.addItem(scatter)
