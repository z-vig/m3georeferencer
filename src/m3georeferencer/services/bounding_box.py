from pydantic import BaseModel, Field
import fiona  # type: ignore
from shapely.geometry import Polygon, mapping  # type: ignore
from pathlib import Path
from uuid import UUID, uuid4
from typing import Literal


def todms(
    dd: float, coord_type: Literal["lon", "lat"], precision: int = 0
) -> str:
    """Convert decimal degrees (-180..180) to DMS with N/S/E/W.

    Args:
        dd: Decimal degrees value.
        coord_type: 'lat' for latitude (N/S) or 'lon' for longitude (E/W').
        precision: Number of decimal places for seconds.

    Returns:
        A string like "123°45'56.78"W" or "12°34'56.78"N".
    """
    if coord_type not in ("lat", "lon"):
        raise ValueError("coord_type must be 'lat' or 'lon'")

    hemi = None
    if coord_type == "lat":
        hemi = "N" if dd >= 0 else "S"
    else:
        hemi = "E" if dd >= 0 else "W"

    total_seconds = round(abs(dd) * 3600, precision)
    degrees = int(total_seconds // 3600)
    remainder = total_seconds - degrees * 3600
    minutes = int(remainder // 60)
    seconds = remainder - minutes * 60

    return f"{degrees}°{minutes}'{seconds:.{precision}f}\"{hemi}"


class Point(BaseModel):
    x: float
    y: float

    def as_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)


class BoundingBox(BaseModel):
    left: float = Field(
        ..., description="The left (minimum x) coordinate of the bounding box."
    )
    bottom: float = Field(
        ...,
        description="The bottom (minimum y) coordinate of the bounding box.",
    )
    right: float = Field(
        ...,
        description="The right (maximum x) coordinate of the bounding box.",
    )
    top: float = Field(
        ..., description="The top (maximum y) coordinate of the bounding box."
    )
    name: str = Field(
        ..., description="A name or identifier for the bounding box."
    )
    id: UUID = Field(
        default_factory=uuid4,
        description="A unique identifier for the bounding box.",
    )

    @property
    def top_left(self) -> Point:
        return Point(x=self.left, y=self.top)

    @property
    def top_right(self) -> Point:
        return Point(x=self.right, y=self.top)

    @property
    def bottom_left(self) -> Point:
        return Point(x=self.left, y=self.bottom)

    @property
    def bottom_right(self) -> Point:
        return Point(x=self.right, y=self.bottom)

    @property
    def shapely_polygon(self) -> Polygon:
        return Polygon(
            [
                self.top_left.as_tuple(),
                self.top_right.as_tuple(),
                self.bottom_right.as_tuple(),
                self.bottom_left.as_tuple(),
            ]
        )

    def __str__(self) -> str:
        space = "    "
        return (
            f"{self.name}:\n"
            f"Decimal Degrees:\n"
            f"{space}Left Boundary: {self.left}\n"
            f"{space}Bottom Boundary: {self.bottom}\n"
            f"{space}Right Boundary: {self.right}\n"
            f"{space}Top Boundary: {self.top}\n"
            f"\nDegrees Minutes Seconds: \n"
            f"{space}Left Boundary: {todms(self.left, coord_type='lon')}\n"
            f"{space}Bottom Boundary: {todms(self.bottom, coord_type='lat')}\n"
            f"{space}Right Boundary: {todms(self.right, coord_type='lon')}\n"
            f"{space}Top Boundary: {todms(self.top, coord_type='lat')}\n"
        )

    def as_csv_row(self) -> str:
        return (
            f"{self.name}, {self.left}, {self.bottom}, {self.right}, "
            f"{self.top}\n"
        )

    def as_extent(
        self, mode: Literal["TopLeft", "BottomLeft"] = "BottomLeft"
    ) -> list[float]:
        if mode == "BottomLeft":
            return [
                self.bottom_left.x,
                self.bottom_left.y,
                self.top_right.x,
                self.top_right.y,
            ]
        elif mode == "TopLeft":
            return [
                self.top_left.x,
                self.top_left.y,
                self.bottom_right.x,
                self.bottom_right.y,
            ]


def to_shapefile(
    bbox: BoundingBox | list[BoundingBox], crs: str, dst_fp: Path | str
) -> None:
    schema = {
        "geometry": "Polygon",
        "properties": {"name": "str"},
    }
    fiona_config = {
        "crs": crs,
        "driver": "ESRI Shapefile",
        "schema": schema,
    }
    bbox_list: list[BoundingBox]
    if isinstance(bbox, list):
        bbox_list = bbox
    else:
        bbox_list = [bbox]

    if Path(dst_fp).is_dir():
        print(f"Writing shapefiles to directory: {dst_fp}")
        for i in bbox_list:
            save = Path(dst_fp, i.name).with_suffix(".shp")
            with fiona.open(save, "w", **fiona_config) as c:
                c.write(
                    {
                        "geometry": mapping(i.shapely_polygon),
                        "properties": {"name": i.name},
                    }
                )
    else:
        save = Path(dst_fp).with_suffix(".shp")
        print(f"Writing to single shapefile: {save}")
        with fiona.open(save, "w", **fiona_config) as c:
            for i in bbox_list:
                c.write(
                    {
                        "geometry": mapping(i.shapely_polygon),
                        "properties": {"name": i.name},
                    }
                )


def to_csv(bbox: list[BoundingBox], dst_fp: Path | str) -> None:
    with open(Path(dst_fp).with_suffix(".csv"), "w") as f:
        f.write(
            "Region, Left_Longitude, Bottom_Latitude, Right_Longitude, "
            "Top_Latitude\n"
        )
        for i in bbox:
            f.write(i.as_csv_row())
