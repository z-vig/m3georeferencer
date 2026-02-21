from PySide6.QtWidgets import QMainWindow, QHBoxLayout, QWidget
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QKeyEvent
from m3georeferencer.services.bounding_box import BoundingBox
from m3georeferencer.services.gcp_model import ImageOffset
from m3georeferencer.services.geotransform import GeotransformModel
from m3georeferencer.ui.widgets import ClickableImage
from pathlib import Path
import rasterio as rio  # type: ignore
import numpy as np


def _open_base_iamge(
    fp: str | Path, bbox: BoundingBox
) -> tuple[np.ndarray, GeotransformModel]:
    dst: rio.DatasetReader
    with rio.open(fp, "r") as dst:
        w = dst.window(
            left=bbox.left, right=bbox.right, top=bbox.top, bottom=bbox.bottom
        )
        arr: np.ndarray = dst.read(window=w)
    gtrans: GeotransformModel = GeotransformModel.fromarraysize(
        upper_left_latitiude=bbox.top,
        upper_left_longitude=bbox.left,
        lower_right_latitude=bbox.bottom,
        lower_right_longitude=bbox.right,
        height=arr.shape[1],
        width=arr.shape[2],
    )
    return arr[0, :, :], gtrans


def _open_target_image(fp: str | Path, offset: ImageOffset) -> np.ndarray:
    dst: rio.DatasetReader
    with rio.open(fp, "r") as dst:
        w = dst.window(
            left=offset.column,
            right=offset.column + offset.width,
            top=offset.row,
            bottom=offset.row + offset.height,
        )
        arr = dst.read(window=w)

    return np.transpose(arr, (1, 2, 0))[:, :, 10]


class MainGeorefWindow(QMainWindow):
    basemap_added = Signal(ClickableImage, GeotransformModel)
    target_added = Signal(ClickableImage, ImageOffset)
    key_pressed = Signal(QKeyEvent)

    def __init__(
        self,
        basemap_image_fp: str | Path,
        target_image_fp: str | Path,
        save_fp: str | Path,
        base_bbox: BoundingBox,
        target_offset: ImageOffset,
        existing_gcps_fp: str | Path | None = None,
    ) -> None:
        super().__init__()
        self._bm_fp = basemap_image_fp
        self._tg_fp = target_image_fp
        self.save_fp = save_fp
        self._bbb = base_bbox
        self._tg_off = target_offset
        self.gcps_fp = existing_gcps_fp

        self.central = QWidget(self)

        self.central_layout = QHBoxLayout()
        self.central.setLayout(self.central_layout)
        self.setCentralWidget(self.central)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()

    def add_basemap(self) -> None:
        _basemap_data, gtrans = _open_base_iamge(self._bm_fp, self._bbb)

        self.basemap_image = ClickableImage()
        self.basemap_image.image_data = _basemap_data
        self.central_layout.addWidget(self.basemap_image)
        self.basemap_added.emit(self.basemap_image, gtrans)

    def add_target(self) -> None:
        _targ_data = _open_target_image(self._tg_fp, self._tg_off)

        self.targ_image = ClickableImage()
        self.targ_image.image_data = _targ_data
        self.central_layout.addWidget(self.targ_image)
        self.target_added.emit(self.targ_image, self._tg_off)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        self.key_pressed.emit(event)
