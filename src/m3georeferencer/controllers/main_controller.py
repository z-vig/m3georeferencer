from pathlib import Path

from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QKeyEvent

from m3georeferencer.ui.main_window import MainGeorefWindow
from m3georeferencer.global_state import AppState
from m3georeferencer.controllers.image_controller import (
    BasemapImageController,
    TargetImageController,
)
from m3georeferencer.services.gcp_model import GCPGroup, GroundControlPoint
from m3georeferencer.pkgtypes import AppMode


class MainController(QObject):
    def __init__(self, window: MainGeorefWindow) -> None:
        super().__init__()
        self._main = window
        self._state = AppState()
        self.targ_control = TargetImageController(self._state)
        self.basemap_control = BasemapImageController(self._state)

        self._connect_signals()

        self._main.add_target()
        self._main.add_basemap()

        if self._main.gcps_fp is not None:
            self._state.gcp_group = GCPGroup.from_gcps_file(self._main.gcps_fp)
            self.targ_control.sync_with_gcp_group()
            self.basemap_control.sync_with_gcp_group()
        else:
            self._state.gcp_group.offset = self.targ_control.offset

    def _connect_signals(self):
        self._main.basemap_added.connect(self.basemap_control.set_img)
        self._main.target_added.connect(self.targ_control.set_img)
        self._main.key_pressed.connect(self.on_key_press)
        self.targ_control.key_pressed.connect(self.on_key_press)
        self.basemap_control.key_pressed.connect(self.on_key_press)

    def on_key_press(self, event: QKeyEvent) -> None:
        if event.key() != Qt.Key.Key_Right:
            return

        if self._state.mode == AppMode.IDLE:
            self.targ_control.img.toggle_border()
            self.targ_control.active = True
        elif self._state.mode == AppMode.TARGETSELECT:
            self.targ_control.img.toggle_border()
            self.targ_control.cache_current()
            self.basemap_control.img.toggle_border()
            self.targ_control.active = False
            self.basemap_control.active = True
        elif self._state.mode == AppMode.BASEMAPSELECT:
            self.basemap_control.img.toggle_border()
            self.basemap_control.cache_current()
            self.basemap_control.active = False
            self.update_gcp_group()
            self.output_gcp_group(save_fp=self._main.save_fp)

        self._state.mode = self._state.mode.next()

    def update_gcp_group(self) -> None:
        base_pt = self.basemap_control.current_point
        targ_pt = self.targ_control.current_point
        gcp = GroundControlPoint(
            pixel_column=targ_pt.x,
            pixel_row=targ_pt.y,
            map_x=base_pt.x,
            map_y=base_pt.y,
        )
        self._state.gcp_group.add_gcp(gcp)
        print(f"Current Number of GCPs: {self._state.gcp_group.ngcp}")

    def output_gcp_group(self, save_fp: str | Path) -> None:
        self._state.gcp_group.write_json(Path(save_fp).with_suffix(".gcps"))
        self._state.gcp_group.write_csv(Path(save_fp).with_suffix(".csv"))
