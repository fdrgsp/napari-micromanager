import string
from pathlib import Path
from typing import Optional, Tuple

import yaml
from pymmcore_plus import CMMCorePlus
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QApplication,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)
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

        self.plate = None

        self._create_gui()

    def _load_plate_info(self) -> list:
        with open(
            PLATE_DATABASE,
        ) as file:
            return yaml.safe_load(file)

    def _create_gui(self):

        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        combo_wdg = QWidget()
        combo_wdg_layout = QHBoxLayout()
        combo_wdg_layout.setSpacing(0)
        combo_wdg.setLayout(combo_wdg_layout)
        self.lbl = QLabel(text="Number of Wells for Calibration:")
        self.lbl.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        self.combo = QComboBox()
        # self.combo.addItems(["1 Well", "4 Wells"])
        self.combo.currentTextChanged.connect(self._enable_table)

        combo_wdg_layout.addWidget(self.lbl)
        combo_wdg_layout.addWidget(self.combo)
        HSpacer = QSpacerItem(20, 40, QSizePolicy.Expanding, QSizePolicy.Minimum)
        combo_wdg_layout.addItem(HSpacer)

        layout.addWidget(combo_wdg)

    def _update_gui(self, plate):

        try:
            self.plate = self._load_plate_info()[plate]
        except KeyError:
            self.plate = None
            return

        self._clear()

        group = QGroupBox()
        group_layout = QGridLayout()
        group_layout.setSpacing(10)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group.setLayout(group_layout)
        self.table_1 = self._general_table_wdg(1)
        self.table_2 = self._general_table_wdg(2)
        self.table_3 = self._general_table_wdg(3)
        self.table_4 = self._general_table_wdg(4)
        group_layout.addWidget(self.table_1, 0, 0)
        group_layout.addWidget(self.table_2, 0, 1)
        group_layout.addWidget(self.table_3, 1, 0)
        group_layout.addWidget(self.table_4, 1, 1)

        self.layout().addWidget(group)

        if self.plate.get("rows") > 1 or self.plate.get("cols") > 1:
            self.combo.clear()
            self.combo.addItems(["1 Well", "4 Wells"])
        else:
            self.combo.clear()
            self.combo.addItems(["1 Well"])

    def _clear(self):
        if self.layout().count() == 1:
            return
        for i in reversed(range(self.layout().count())):
            if i == 0:
                return
            if item := self.layout().takeAt(i):
                if wdg := item.widget():
                    if isinstance(wdg, QGroupBox):
                        wdg.setParent(None)
                        wdg.deleteLater()

    def _general_table_wdg(self, position: int):

        if position > 4:
            raise ValueError("Value must be between 1 and 4")

        wdg = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(10)
        wdg.setLayout(layout)

        lbl = QLabel()
        lbl.setAlignment(Qt.AlignCenter)
        rows = self.plate.get("rows")
        cols = self.plate.get("cols")

        if position == 1:
            lbl.setText(f"Well {ALPHABET[0]}1")
        elif position == 2:
            lbl.setText(f"Well {ALPHABET[0]}{cols}")
        elif position == 3:
            lbl.setText(f"Well {ALPHABET[rows - 1]}1")
        elif position == 4:
            lbl.setText(f"Well {ALPHABET[rows - 1]}{cols}")

        layout.addWidget(lbl)

        tb = QTableWidget()
        hdr = tb.horizontalHeader()
        hdr.setSectionResizeMode(hdr.Stretch)
        tb.verticalHeader().setVisible(False)
        tb.setTabKeyNavigation(True)
        tb.setColumnCount(2)
        tb.setRowCount(0)
        tb.setHorizontalHeaderLabels(["X", "Y"])
        layout.addWidget(tb)

        btn_wdg = QWidget()
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_wdg.setLayout(btn_layout)
        add_btn = QPushButton(text="Add")
        clear_btn = QPushButton(text="Clear")
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(clear_btn)

        layout.addWidget(btn_wdg)

        return wdg

    def _enable_table(self, text: str):
        if not self.plate:
            self.table_1.setEnabled(False)
            self.table_2.setEnabled(False)
            self.table_3.setEnabled(False)
            self.table_4.setEnabled(False)
        elif text == "1 Well":
            self.table_2.setEnabled(False)
            self.table_3.setEnabled(False)
            self.table_4.setEnabled(False)
        else:
            self.table_2.setEnabled(True)
            self.table_3.setEnabled(True)
            self.table_4.setEnabled(True)


if __name__ == "__main__":

    app = QApplication([])
    window = PlateCalibration()
    window.show()
    app.exec_()


a = (-2.0, 2.0)
b = (5.0, 1.0)
c = (-2.0, -6.0)


def get_center_of_round_well(
    a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]
) -> Tuple[float, float]:
    """Find the center of a round well given 3 edge points"""
    # eq circle (x - x1)^2 + (y - y1)^2 = r^2
    # for point a: (x - ax)^2 + (y - ay)^2 = r^2
    # for point b: = (x - bx)^2 + (y - by)^2 = r^2
    # for point c: = (x - cx)^2 + (y - cy)^2 = r^2

    x, y = symbols("x y")

    eq1 = Eq((x - a[0]) ** 2 + (y - a[1]) ** 2, (x - b[0]) ** 2 + (y - b[1]) ** 2)
    eq2 = Eq((x - a[0]) ** 2 + (y - a[1]) ** 2, (x - c[0]) ** 2 + (y - c[1]) ** 2)

    dict_center = solve((eq1, eq2), (x, y))
    xc = dict_center[x]
    yc = dict_center[y]
    return xc, yc


xc, yc = get_center_of_round_well(a, b, c)
print(xc, yc)


a = (0.0, 2.0)
b = (7.0, 5.0)
c = (8, 4)
d = (7, 0)


def get_center_of_squared_well(
    a: Tuple[float, float],
    b: Tuple[float, float],
    c: Tuple[float, float],
    d: Tuple[float, float],
) -> Tuple[float, float]:
    """Find the center of a square well given 4 edge points"""
    x_list = [x[0] for x in [a, b, c, d]]
    y_list = [y[1] for y in [a, b, c, d]]

    x_max, x_min = (max(x_list), min(x_list))
    y_max, y_min = (max(y_list), min(y_list))

    xc = (x_max - x_min) / 2
    yc = (y_max - y_min) / 2

    return xc, yc


xc, yc = get_center_of_squared_well(a, b, c, d)
print(xc, yc)
