import string
from pathlib import Path
from typing import Optional, Tuple

import yaml
from fonticon_mdi6 import MDI6
from pymmcore_plus import CMMCorePlus
from qtpy.QtCore import QSize, Qt
from qtpy.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from superqt.fonticon import icon
from sympy import Eq, solve, symbols

from micromanager_gui._core import get_core_singleton

PLATE_DATABASE = Path(__file__).parent / "_well_plate.yaml"
ALPHABET = string.ascii_uppercase


class PlateCalibration(QWidget):
    def __init__(
        self,
        # viewer: napari.viewer.Viewer,
        parent: Optional[QWidget] = None,
        *,
        mmcore: Optional[CMMCorePlus] = None,
    ):
        super().__init__(parent)

        self._mmc = mmcore or get_core_singleton()
        # self.viever = viewer

        # self._mmc.loadSystemConfiguration()  # to remove

        self.plate = None
        self.wells_dict = {}
        self.is_calibrated = False

        self._create_gui()

    def _create_gui(self):

        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(layout)

        combo_wdg = QWidget()
        combo_wdg_layout = QHBoxLayout()
        combo_wdg_layout.setSpacing(0)
        combo_wdg_layout.setContentsMargins(0, 0, 0, 5)
        combo_wdg.setLayout(combo_wdg_layout)
        self.lbl = QLabel(text="Number of Wells for Calibration:")
        self.lbl.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        self.n_calib_wells_combo = QComboBox()
        self.n_calib_wells_combo.currentTextChanged.connect(self._enable_table)
        combo_wdg_layout.addWidget(self.lbl)
        combo_wdg_layout.addWidget(self.n_calib_wells_combo)
        HSpacer = QSpacerItem(20, 40, QSizePolicy.Expanding, QSizePolicy.Minimum)
        combo_wdg_layout.addItem(HSpacer)
        layout.addWidget(combo_wdg)

        self.info_lbl = QLabel()
        layout.addWidget(self.info_lbl)

        group = QGroupBox()
        self.group_layout = QGridLayout()
        self.group_layout.setSpacing(10)
        self.group_layout.setContentsMargins(0, 0, 0, 0)
        group.setLayout(self.group_layout)
        layout.addWidget(group)

        bottom_group = QGroupBox()
        bottom_group_layout = QHBoxLayout()
        bottom_group_layout.setSpacing(10)
        bottom_group_layout.setContentsMargins(10, 10, 10, 10)
        bottom_group.setLayout(bottom_group_layout)

        calibrate_btn = QPushButton(text="Calibrate Plate")
        calibrate_btn.clicked.connect(self._calibrate_plate)
        self.icon_lbl = QLabel()
        self.icon_lbl.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        self.icon_lbl.setPixmap(
            icon(MDI6.close_octagon_outline, color="magenta").pixmap(QSize(30, 30))
        )

        self.cal_lbl = QLabel()
        self.cal_lbl.setText("Plate non Calibrated!")

        bottom_group_layout.addWidget(calibrate_btn)
        bottom_group_layout.addWidget(self.icon_lbl)
        bottom_group_layout.addWidget(self.cal_lbl)

        layout.addWidget(bottom_group)

    def _load_plate_info(self) -> list:
        with open(
            PLATE_DATABASE,
        ) as file:
            return yaml.safe_load(file)

    def _update_gui(self, plate):

        if self.plate and self.plate.get("id") == plate:
            return

        self.is_calibrated = False
        self.wells_dict.clear()
        self.icon_lbl.setPixmap(
            icon(MDI6.close_octagon_outline, color="magenta").pixmap(QSize(30, 30))
        )
        self.cal_lbl.setText("Plate non Calibrated!")

        try:
            self.plate = self._load_plate_info()[plate]
        except KeyError:
            self.plate = None
            return

        self._clear_tables()

        self.table_1 = CalibrationTable(self.plate, 1)
        self.table_2 = CalibrationTable(self.plate, 2)
        self.table_3 = CalibrationTable(self.plate, 3)
        self.table_4 = CalibrationTable(self.plate, 4)
        self.group_layout.addWidget(self.table_1, 0, 0)
        self.group_layout.addWidget(self.table_2, 0, 1)
        self.group_layout.addWidget(self.table_3, 1, 0)
        self.group_layout.addWidget(self.table_4, 1, 1)

        if self.plate.get("rows") > 1 or self.plate.get("cols") > 1:
            self.n_calib_wells_combo.clear()
            self.n_calib_wells_combo.addItems(["1 Well", "4 Wells"])
        else:
            self.n_calib_wells_combo.clear()
            self.n_calib_wells_combo.addItems(["1 Well"])

    def _clear_tables(self):
        for i in reversed(range(self.group_layout.count())):
            if item := self.group_layout.takeAt(i):
                if wdg := item.widget():
                    wdg.setParent(None)
                    wdg.deleteLater()

    def _enable_table(self, text: str):
        if not self.plate:
            self.table_1.setEnabled(False)
            self.table_2.setEnabled(False)
            self.table_3.setEnabled(False)
            self.table_4.setEnabled(False)
            text = ""
        elif text == "1 Well":
            self.table_2.setEnabled(False)
            self.table_3.setEnabled(False)
            self.table_4.setEnabled(False)
            text = (
                f"Add {3 if self.plate.get('circular') else 4} "
                f"points on the edge of well {self.table_1.well_lbl.text()}."
            )
        else:
            self.table_2.setEnabled(True)
            self.table_3.setEnabled(True)
            self.table_4.setEnabled(True)
            text = (
                f"Add {3 if self.plate.get('circular') else 4} "
                f"points on the edge of wells {self.table_1.well_lbl.text()}, "
                f"{self.table_2.well_lbl.text()}, {self.table_3.well_lbl.text()} "
                f"and {self.table_4.well_lbl.text()}"
            )
        self.info_lbl.setText(text)

    def get_center_of_round_well(
        self, a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]
    ) -> Tuple[float, float]:
        """Find the center of a round well given 3 edge points"""
        # eq circle (x - x1)^2 + (y - y1)^2 = r^2
        # for point a: (x - ax)^2 + (y - ay)^2 = r^2
        # for point b: = (x - bx)^2 + (y - by)^2 = r^2
        # for point c: = (x - cx)^2 + (y - cy)^2 = r^2

        print(a[0], a[1])

        x, y = symbols("x y")

        eq1 = Eq((x - a[0]) ** 2 + (y - a[1]) ** 2, (x - b[0]) ** 2 + (y - b[1]) ** 2)
        eq2 = Eq((x - a[0]) ** 2 + (y - a[1]) ** 2, (x - c[0]) ** 2 + (y - c[1]) ** 2)

        if dict_center := solve((eq1, eq2), (x, y)):
            xc = dict_center[x]
            yc = dict_center[y]
        else:
            raise ValueError("Invalid Coordinates!")

        return xc, yc

    def get_center_of_squared_well(
        self,
        a: Tuple[float, float],
        b: Tuple[float, float],
        c: Tuple[float, float],
        d: Tuple[float, float],
    ) -> Tuple[float, float]:
        """Find the center of a square well given 4 edge points"""

        print(a[0], a[1])

        x_list = [x[0] for x in [a, b, c, d]]
        y_list = [y[1] for y in [a, b, c, d]]

        x_max, x_min = (max(x_list), min(x_list))
        y_max, y_min = (max(y_list), min(y_list))

        xc = (x_max - x_min) / 2
        yc = (y_max - y_min) / 2

        return xc, yc

    def _calibrate_plate(self):

        calib_wells = self.n_calib_wells_combo.currentText()

        if calib_wells == "1 Well":
            if self.table_1.tb.rowCount() < (3 if self.plate.get("circular") else 4):
                raise ValueError(
                    f"Not enough points for well {self.table_1.well_lbl.text()}."
                )
        elif (
            self.table_1.tb.rowCount() < (3 if self.plate.get("circular") else 4)
            or self.table_2.tb.rowCount() < (3 if self.plate.get("circular") else 4)
            or self.table_3.tb.rowCount() < (3 if self.plate.get("circular") else 4)
            or self.table_4.tb.rowCount() < (3 if self.plate.get("circular") else 4)
        ):
            raise ValueError(
                f"Not enough points for one or more of wells "
                f"{self.table_1.well_lbl.text()}, {self.table_2.well_lbl.text()}, "
                f"{self.table_3.well_lbl.text()} and/or {self.table_4.well_lbl.text()}."
            )

        # for now only implement 1 well
        # later on: if calib_wells == "1 Well":
        pos = ()
        for r in range(3 if self.plate.get("circular") else 4):
            x = float(self.table_1.tb.item(r, 0).text())
            y = float(self.table_1.tb.item(r, 1).text())
            pos += ((x, y),)

        if self.plate.get("circular"):
            xc, yc = self.get_center_of_round_well(*pos)
        else:
            xc, yc = self.get_center_of_squared_well(*pos)

        print(xc, yc)

        self.wells_dict.clear()
        self.wells_dict = {f"{self.table_1.well_lbl.text()}": (xc, yc)}
        print(self.wells_dict)

        self.is_calibrated = True
        self.icon_lbl.setPixmap(
            icon(MDI6.check_bold, color=(0, 255, 0)).pixmap(QSize(20, 20))
        )
        self.cal_lbl.setText("Plate Calibrated!")


class CalibrationTable(QWidget):
    def __init__(
        self, plate: dict, position: int, *, mmcore: Optional[CMMCorePlus] = None
    ):
        super().__init__()

        if position > 4:
            raise ValueError("Value must be between 1 and 4")

        self._plate = plate
        self.position = position
        self._mmc = mmcore or get_core_singleton()

        self._create_wdg()

    def _create_wdg(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        self.setLayout(layout)

        self.well_lbl = QLabel()
        self.well_lbl.setAlignment(Qt.AlignCenter)
        rows = self._plate.get("rows")
        cols = self._plate.get("cols")

        if self.position == 1:
            self.well_lbl.setText(f"{ALPHABET[0]}1")
        elif self.position == 2:
            self.well_lbl.setText(f"{ALPHABET[0]}{cols}")
        elif self.position == 3:
            self.well_lbl.setText(f"{ALPHABET[rows - 1]}1")
        elif self.position == 4:
            self.well_lbl.setText(f"{ALPHABET[rows - 1]}{cols}")

        layout.addWidget(self.well_lbl)

        self.tb = QTableWidget()
        hdr = self.tb.horizontalHeader()
        hdr.setSectionResizeMode(hdr.Stretch)
        self.tb.verticalHeader().setVisible(False)
        self.tb.setTabKeyNavigation(True)
        self.tb.setColumnCount(2)
        self.tb.setRowCount(0)
        self.tb.setHorizontalHeaderLabels(["X", "Y"])
        self.tb.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.tb)

        btn_wdg = QWidget()
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_wdg.setLayout(btn_layout)
        add_btn = QPushButton(text="Add")
        add_btn.clicked.connect(self._add_pos)
        remove_btn = QPushButton(text="Remove")
        remove_btn.clicked.connect(self._remove_position_row)
        clear_btn = QPushButton(text="Clear")
        clear_btn.clicked.connect(self._clear_table)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)
        btn_layout.addWidget(clear_btn)

        layout.addWidget(btn_wdg)

    def _add_pos(self):

        if not self._mmc.getXYStageDevice():
            return

        if len(self._mmc.getLoadedDevices()) > 1:
            idx = self._add_position_row()

            for c, ax in enumerate("XY"):
                cur = getattr(self._mmc, f"get{ax}Position")()
                item = QTableWidgetItem(str(cur))
                item.setTextAlignment(int(Qt.AlignHCenter | Qt.AlignVCenter))
                self.tb.setItem(idx, c, item)

    def _add_position_row(self) -> int:
        idx = self.tb.rowCount()
        self.tb.insertRow(idx)
        return idx

    def _remove_position_row(self):
        rows = {r.row() for r in self.tb.selectedIndexes()}
        for idx in sorted(rows, reverse=True):
            self.tb.removeRow(idx)

    def _clear_table(self):
        self.tb.clearContents()
        self.tb.setRowCount(0)

    def get_positions(self):
        pass


# a = (-2.0, 2.0)
# b = (5.0, 1.0)
# c = (-2.0, -6.0)
# a = (0.0,0.0)
# b = (0.0,0.0)
# c = (0.0,0.0)


# def get_center_of_round_well(
#     a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]
# ) -> Tuple[float, float]:
#     """Find the center of a round well given 3 edge points"""
#     # eq circle (x - x1)^2 + (y - y1)^2 = r^2
#     # for point a: (x - ax)^2 + (y - ay)^2 = r^2
#     # for point b: = (x - bx)^2 + (y - by)^2 = r^2
#     # for point c: = (x - cx)^2 + (y - cy)^2 = r^2

#     x, y = symbols("x y")

#     eq1 = Eq((x - a[0]) ** 2 + (y - a[1]) ** 2, (x - b[0]) ** 2 + (y - b[1]) ** 2)
#     eq2 = Eq((x - a[0]) ** 2 + (y - a[1]) ** 2, (x - c[0]) ** 2 + (y - c[1]) ** 2)

#     if dict_center := solve((eq1, eq2), (x, y)):
#         xc = dict_center[x]
#         yc = dict_center[y]
#     else:
#         raise ValueError("Coordinates not valid!")

#     return xc, yc


# # xc, yc = get_center_of_round_well(a, b, c)
# get_center_of_round_well(a, b, c)
# print(xc, yc)


# a = (0.0, 2.0)
# b = (7.0, 5.0)
# c = (8, 4)
# d = (7, 0)


# def get_center_of_squared_well(
#     a: Tuple[float, float],
#     b: Tuple[float, float],
#     c: Tuple[float, float],
#     d: Tuple[float, float],
# ) -> Tuple[float, float]:
#     """Find the center of a square well given 4 edge points"""
#     x_list = [x[0] for x in [a, b, c, d]]
#     y_list = [y[1] for y in [a, b, c, d]]

#     x_max, x_min = (max(x_list), min(x_list))
#     y_max, y_min = (max(y_list), min(y_list))

#     xc = (x_max - x_min) / 2
#     yc = (y_max - y_min) / 2

#     return xc, yc


# xc, yc = get_center_of_squared_well(a, b, c, d)
# print(xc, yc)
