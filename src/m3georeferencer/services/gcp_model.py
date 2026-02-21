from dataclasses import dataclass
import numpy as np
from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from pathlib import Path
from typing_extensions import Self
import xarray as xr
import re


@dataclass
class Point:
    x: float
    y: float


class GroundControlPoint(BaseModel):
    pixel_row: float = Field(
        ..., description="Pixel row coordinate of the GCP"
    )
    pixel_column: float = Field(
        ..., description="Pixel column coordinate of the GCP"
    )
    map_x: float = Field(..., description="Map x coordinate of the GCP")
    map_y: float = Field(..., description="Map y coordinate of the GCP")
    id: UUID = Field(
        default_factory=uuid4, description="Unique identifier for the GCP"
    )


class ImageOffset(BaseModel):
    height: int = Field(..., description="Height of the image")
    width: int = Field(..., description="Width of the image")
    row: int = Field(..., description="Row offset for the image")
    column: int = Field(..., description="Column offset for the image")

    @property
    def row_slice(self) -> slice:
        return slice(self.row, self.row + self.height - 1)

    @property
    def col_slice(self) -> slice:
        return slice(self.column, self.column + self.width - 1)

    def crop_image(
        self, base_image: np.ndarray | xr.DataArray
    ) -> np.ndarray | xr.DataArray:
        """
        Extract the offset image from a corresponding base image.
        """
        if (base_image.shape[0] < self.row + self.height) or (
            base_image.shape[1] < self.column + self.width
        ):
            raise ValueError(
                "Input image (size:"
                f"{base_image.shape[0], base_image.shape[1]}) is too small for"
                " the offset size ({self.height, self.width})."
            )

        return base_image[self.row_slice, self.col_slice]


class GCPGroup(BaseModel):
    offset: ImageOffset
    gcp_list: list[GroundControlPoint]

    @classmethod
    def from_txt(cls, file_path: Path | str, headerrows: int = 7) -> Self:
        data = np.loadtxt(
            file_path, dtype="<U36", skiprows=headerrows, delimiter=","
        )
        good_cols = []
        for i in range(data.shape[1]):
            if np.all(data[:, i] == " "):
                continue
            good_cols.append(i)

        data = data[:, np.array(good_cols)]

        gcp_list: list[GroundControlPoint] = []
        for idx in range(data.shape[0]):
            row = data[idx, :]
            gcp = GroundControlPoint(
                pixel_row=row[1],
                pixel_column=row[2],
                map_x=row[3],
                map_y=row[4],
            )
            gcp_list.append(gcp)

        hdr_pattern = re.compile(r"Source for Target Image:[\s\S]*?ID")
        with open(file_path, "r") as f:
            file_content = f.read()
            test = re.search(hdr_pattern, file_content)
        if test is None:
            raise ValueError(f"Invalid File Header: {file_content}")
        header = file_content[slice(*test.span())]
        header_lines = header.split("\n")

        search_list = [
            re.search(r"([\s\S]*?):([\s\S]*)", i) for i in header_lines[:-1]
        ]
        header_dict: dict[str, int] = {}
        for item in search_list:
            if item is not None:
                g = item.groups()
                try:
                    header_dict[g[0]] = int(g[1])
                except ValueError:
                    continue

        offset = ImageOffset(
            height=header_dict["Target Image Height"],
            width=header_dict["Target Image Width"],
            row=header_dict["Row Offset"],
            column=header_dict["Column Offset"],
        )

        return cls(
            offset=offset,
            gcp_list=gcp_list,
        )

    @classmethod
    def from_gcps_file(cls, fp: Path | str) -> Self:
        with open(fp, "r") as f:
            json = f.read()
        return cls.model_validate_json(json)

    @classmethod
    def empty(cls) -> Self:
        return cls(
            offset=ImageOffset(height=0, width=0, row=0, column=0), gcp_list=[]
        )

    @property
    def ngcp(self) -> int:
        return len(self.gcp_list)

    @property
    def row_pixels(self) -> np.ndarray:
        return np.array([gcp.pixel_row for gcp in self.gcp_list])

    @property
    def col_pixels(self) -> np.ndarray:
        return np.array([gcp.pixel_column for gcp in self.gcp_list])

    @property
    def map_x(self) -> np.ndarray:
        return np.array([gcp.map_x for gcp in self.gcp_list])

    @property
    def map_y(self) -> np.ndarray:
        return np.array([gcp.map_y for gcp in self.gcp_list])

    def add_gcp(self, gcp: GroundControlPoint):
        self.gcp_list.append(gcp)

    def write_json(self, fp: Path | str) -> None:
        with open(Path(fp).with_suffix(".gcps"), "w") as f:
            f.write(self.model_dump_json(indent=2))

    def write_csv(self, fp: Path | str) -> None:
        with open(Path(fp).with_suffix(".csv"), "w") as f:
            f.write("Index, Pixel Row, Pixel Column, Map X, Map Y, ID\n")
            for n, i in enumerate(self.gcp_list):
                f.write(
                    f"{n}, {i.pixel_row}, {i.pixel_column}, {i.map_x},"
                    f" {i.map_y}, {i.id}\n"
                )

    def __add__(self, value: Self) -> Self:
        for i in value.gcp_list:
            self.add_gcp(i)

        return self


if __name__ == "__main__":
    gcp1 = "D:/moon_data/m3/Gruithuisen_Region/gcps_files/M3G20090208T160125.gcps"  # noqa
    gcp2 = "D:/moon_data/m3/Gruithuisen_Region/new_gcps_160125.gcps"

    mod1 = GCPGroup.from_gcps_file(gcp1)
    mod2 = GCPGroup.from_txt(gcp2)

    mod3 = mod1 + mod2

    print(mod1.ngcp)
    print(mod2.ngcp)
    print(mod3.ngcp)

    mod3.write_json(
        "D:/moon_data/m3/Gruithuisen_Region/gcps_files/new_test.gcps"
    )
    mod3.write_csv(
        "D:/moon_data/m3/Gruithuisen_Region/gcps_files/new_test.csv"
    )
