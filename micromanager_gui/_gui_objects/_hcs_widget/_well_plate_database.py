from __future__ import annotations

import re


class WellPlate:
    def __init__(self):
        super().__init__()

        self.plates = ["Standard 6", "Standard 12", "Standard 24", "Standard 96"]

        self.plate_name = ""
        self._wells = 0
        self.rows = 0
        self.cols = 0
        self.well_to_well_spacing = 0
        self.well_radius = 0

        self.drawing_diameter = 0
        self.text_size = 0

    @classmethod
    def set_format(cls, key: str) -> WellPlate:
        if "Standard" in key:
            if match := re.search(r"(\d{1,4})", key):
                wells = int(match.groups()[0])
                return Standard(wells)

        print(f"{key} not yet implemented")

    def get_name(self) -> str:
        return self.plate_name

    def add_plate(self, well_plate: str) -> None:
        self.plates.append(well_plate)

    def get_n_wells(self) -> int:
        return self._wells

    def get_n_rows(self) -> int:
        return self.rows

    def get_n_columns(self) -> int:
        return self.cols

    def get_well_distance(self) -> float:
        return self.well_to_well_spacing

    def get_well_radius(self) -> float:
        return self.well_radius

    def get_drawing_diameter(self) -> int:
        return self.drawing_diameter

    def get_text_size(self) -> str:
        return self.text_size


class Standard(WellPlate):
    """Standard well plates"""

    def __init__(self, wells: int):
        super().__init__()

        self._wells = wells

        (
            self.plate_name,
            self.rows,
            self.cols,
            self.drawing_diameter,
            self.text_size,
            self.well_to_well_spacing,
            self.well_radius,
        ) = self._get_well_parameters(self._wells)

    def _get_well_parameters(self, wells: int):
        if wells == 6:
            rows = 2
            cols = 3
            drawing_diameter = 115
            text_size = 20
            well_to_well_spacing = 39.12
            well_radius = 34.9
        elif wells == 12:
            rows = 3
            cols = 4
            drawing_diameter = 75
            text_size = 18
            well_to_well_spacing = 26.0
            well_radius = 22.0
        elif wells == 24:
            rows = 4
            cols = 6
            drawing_diameter = 55
            text_size = 16
            well_to_well_spacing = 19.3
            well_radius = 15.5
        elif wells == 96:
            rows = 8
            cols = 12
            drawing_diameter = 25
            text_size = 10
            well_to_well_spacing = 9.0
            well_radius = 6.2

        plate_name = f"Standard {wells}"

        return (
            plate_name,
            rows,
            cols,
            drawing_diameter,
            text_size,
            well_to_well_spacing,
            well_radius,
        )
