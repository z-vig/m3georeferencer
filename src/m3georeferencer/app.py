# flake8: noqa

from PySide6.QtWidgets import QApplication

from m3georeferencer.ui.main_window import MainGeorefWindow
from m3georeferencer.controllers.main_controller import MainController
from m3georeferencer.services.bounding_box import BoundingBox
from m3georeferencer.services.gcp_model import ImageOffset


def m3georeferencer():
    app = QApplication([])

    main = MainGeorefWindow(
        basemap_image_fp="D:/moon_data/LRO_camera/WAC/LRO_WAC_Global_Mosaic_GCSMOON2000.tif",
        target_image_fp="D:/moon_data/m3/Gruithuisen_Region/M3G20090208T160125/pds_data/L1/M3G20090208T160125_V03_RDN.IMG",
        save_fp="D:/moon_data/m3/Gruithuisen_Region/gcps_files/M3G20090208T160125.gcps",
        base_bbox=BoundingBox(
            name="GDomes", left=-42, bottom=32, right=-37, top=43
        ),
        target_offset=ImageOffset(height=2000, width=304, row=5000, column=0),
        existing_gcps_fp="D:/moon_data/m3/Gruithuisen_Region/gcps_files/M3G20090208T160125.gcps",
    )
    controller = MainController(main)

    main.show()
    app.exec()


def main():
    m3georeferencer()


if __name__ == "__main__":
    main()
