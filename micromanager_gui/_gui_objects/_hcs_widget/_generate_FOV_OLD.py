import math
import random

import numpy as np
from qtpy.QtCore import QRectF, Qt
from qtpy.QtGui import QPen
from qtpy.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QGraphicsItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from superqt.utils import signals_blocked

AlignCenter = Qt.AlignmentFlag.AlignCenter


class SelectFOV(QWidget):
    def __init__(self):
        super().__init__()

        self._size_x = None
        self._size_y = None
        self._is_circular = None

        self._create_widget()

        self._set_enabled(False)

    def _create_widget(self):

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)
        self.setLayout(main_layout)

        left_wdg = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        left_wdg.setLayout(layout)

        fov_label = QLabel()
        fov_label.setMinimumWidth(120)
        fov_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        fov_label.setText("Selection mode:")
        self.FOV_selection_mode_combo = QComboBox()
        self.FOV_selection_mode_combo.addItems(["Random", "Center"])
        self.FOV_selection_mode_combo.currentTextChanged.connect(
            self._on_FOV_selection_changed
        )
        mode = self._make_QHBoxLayout_wdg_with_label(
            fov_label, self.FOV_selection_mode_combo
        )
        layout.addWidget(mode)

        self.plate_area_label_x = QLabel()
        self.plate_area_label_x.setMinimumWidth(120)
        self.plate_area_label_x.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.plate_area_label_x.setText("Area FOV x (mm):")
        self.plate_area_x = QDoubleSpinBox()
        self.plate_area_x.setAlignment(AlignCenter)
        self.plate_area_x.setMinimum(1)
        self.plate_area_x.valueChanged.connect(self._on_area_x_changed)
        _plate_area_x = self._make_QHBoxLayout_wdg_with_label(
            self.plate_area_label_x, self.plate_area_x
        )
        layout.addWidget(_plate_area_x)

        self.plate_area_label_y = QLabel()
        self.plate_area_label_y.setMinimumWidth(120)
        self.plate_area_label_y.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.plate_area_label_y.setText("Area FOV y (mm):")
        self.plate_area_y = QDoubleSpinBox()
        self.plate_area_y.setAlignment(AlignCenter)
        self.plate_area_y.setMinimum(1)
        self.plate_area_y.valueChanged.connect(self._on_area_y_changed)
        _plate_area_y = self._make_QHBoxLayout_wdg_with_label(
            self.plate_area_label_y, self.plate_area_y
        )
        layout.addWidget(_plate_area_y)

        number_of_FOV_label = QLabel()
        number_of_FOV_label.setMinimumWidth(120)
        number_of_FOV_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        number_of_FOV_label.setText("Number of FOV:")
        self.number_of_FOV = QSpinBox()
        self.number_of_FOV.setAlignment(AlignCenter)
        self.number_of_FOV.setMinimum(1)
        self.number_of_FOV.setMaximum(100)
        self.number_of_FOV.valueChanged.connect(self._on_number_of_FOV_changed)
        nFOV = self._make_QHBoxLayout_wdg_with_label(
            number_of_FOV_label, self.number_of_FOV
        )
        layout.addWidget(nFOV)

        self.random_button = QPushButton(text="New Random FOV(s)")
        self.random_button.clicked.connect(self._on_random_button_pressed)
        layout.addWidget(self.random_button)

        main_layout.addWidget(left_wdg)

        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene, self)
        self.view.setStyleSheet("background:grey;")
        self.view.setFixedSize(200, 150)

        main_layout.addWidget(self.view)

    def _set_enabled(self, enabled: bool):
        self.FOV_selection_mode_combo.setEnabled(enabled)
        self.random_button.setEnabled(enabled)
        self.number_of_FOV.setEnabled(enabled)
        self.plate_area_x.setEnabled(enabled)
        self.plate_area_y.setEnabled(enabled)

    def _make_QHBoxLayout_wdg_with_label(self, label: QLabel, wdg: QWidget):
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        layout.addWidget(label)
        layout.addWidget(wdg)
        widget.setLayout(layout)
        return widget

    def _on_FOV_selection_changed(self, value: str):

        self.random_button.setEnabled(value == "Random")
        self.number_of_FOV.setEnabled(value == "Random")
        self.plate_area_x.setEnabled(value == "Random")
        self.plate_area_x.setValue(self._size_x)
        if not self._is_circular:
            self.plate_area_y.setEnabled(value == "Random")
            self.plate_area_y.setValue(self._size_y)

        self.scene.clear()

        nFOV = self.number_of_FOV.value()
        area_x = self.plate_area_x.value()
        area_y = self.plate_area_y.value()

        self._set_FOV_and_mode(nFOV, value, area_x, area_y)

    def _on_area_x_changed(self, value: int):

        self.scene.clear()

        mode = self.FOV_selection_mode_combo.currentText()
        nFOV = self.number_of_FOV.value()
        area_y = self.plate_area_y.value()

        self._set_FOV_and_mode(nFOV, mode, value, area_y)

    def _on_area_y_changed(self, value: int):

        self.scene.clear()

        mode = self.FOV_selection_mode_combo.currentText()
        nFOV = self.number_of_FOV.value()
        area_x = self.plate_area_x.value()

        self._set_FOV_and_mode(nFOV, mode, area_x, value)

    def _on_number_of_FOV_changed(self, value: int):

        self.scene.clear()

        mode = self.FOV_selection_mode_combo.currentText()
        area_x = self.plate_area_x.value()
        area_y = self.plate_area_y.value()

        self._set_FOV_and_mode(value, mode, area_x, area_y)

    def _load_plate_info(self, size_x, size_y, is_circular):

        self.FOV_selection_mode_combo.setEnabled(True)

        self._size_x = size_x
        self._size_y = size_y
        self._is_circular = is_circular

        enable = self.FOV_selection_mode_combo.currentText() == "Random"
        self.random_button.setEnabled(enable)
        self.number_of_FOV.setEnabled(enable)
        self.plate_area_x.setEnabled(enable)

        self.plate_area_x.setMaximum(self._size_x)
        with signals_blocked(self.plate_area_x):
            self.plate_area_x.setValue(self._size_x)
        self.plate_area_y.setMaximum(self._size_y)
        with signals_blocked(self.plate_area_y):
            self.plate_area_y.setValue(self._size_y)

        self.plate_area_y.setEnabled(not self._is_circular)

        self._on_random_button_pressed()

    def _on_random_button_pressed(self):
        self.scene.clear()
        mode = self.FOV_selection_mode_combo.currentText()
        nFOV = self.number_of_FOV.value()
        area_x = self.plate_area_x.value()
        area_y = self.plate_area_y.value()
        self._set_FOV_and_mode(nFOV, mode, area_x, area_y)

    def _set_FOV_and_mode(self, nFOV: int, mode: str, area_x: float, area_y: float):

        max_size_y = 140

        main_pen = QPen(Qt.magenta)
        main_pen.setWidth(4)
        area_pen = QPen(Qt.green)
        area_pen.setWidth(4)

        if self._is_circular:
            self.scene.addEllipse(0, 0, max_size_y, max_size_y, main_pen)

            if mode == "Center":
                self.scene.clear()
                self.scene.addEllipse(0, 0, max_size_y, max_size_y, area_pen)
                center_x, center_y = (max_size_y / 2, max_size_y / 2)
                self.scene.addItem(
                    FOVPoints(
                        center_x, center_y, 5, 5, "Center", max_size_y, max_size_y
                    )
                )

            elif mode == "Random":
                diameter = (max_size_y * area_x) / self._size_x
                center = (max_size_y - diameter) / 2

                fov_area = QRectF(center, center, diameter, diameter)
                self.scene.addEllipse(fov_area, area_pen)

                points = self._random_points_in_circle(nFOV, diameter, center)
                for p in points:
                    self.scene.addItem(
                        FOVPoints(p[0], p[1], 5, 5, "Random", max_size_y, max_size_y)
                    )

        else:
            max_size_x = 140 if self._size_x == self._size_y else 190

            self.scene.addRect(0, 0, max_size_x, max_size_y, main_pen)

            if mode == "Center":
                self.scene.clear()
                self.scene.addRect(0, 0, max_size_x, max_size_y, area_pen)
                center_x, center_y = (max_size_x / 2, max_size_y / 2)
                self.scene.addItem(
                    FOVPoints(
                        center_x, center_y, 5, 5, "Center", max_size_x, max_size_y
                    )
                )

            elif mode == "Random":
                size_x = (max_size_x * area_x) / self._size_x
                size_y = (max_size_y * area_y) / self._size_y
                center_x = (max_size_x - size_x) / 2
                center_y = (max_size_y - size_y) / 2

                fov_area = QRectF(center_x, center_y, size_x, size_y)
                self.scene.addRect(fov_area, area_pen)

                points = self._random_points_in_square(
                    nFOV, size_x, size_y, max_size_x, max_size_y
                )
                for p in points:
                    self.scene.addItem(
                        FOVPoints(p[0], p[1], 5, 5, "Random", max_size_x, max_size_y)
                    )

    def _random_points_in_circle(self, nFOV, diameter: float, center):
        points = []
        radius = diameter / 2
        for _ in range(nFOV):
            # random angle
            alpha = 2 * math.pi * random.random()
            # random radius
            # r = (radius - 5) * math.sqrt(random.random())  # -5 because of point size
            r = radius * math.sqrt(random.random())  # -5 because of point size
            # calculating coordinates
            x = r * math.cos(alpha) + center + radius
            y = r * math.sin(alpha) + center + radius
            points.append((x, y))
        return points

    def _random_points_in_square(self, nFOV, size_x, size_y, max_size_x, max_size_y):
        # x_left = ((max_size_x - size_x) / 2) + 5  # left bound
        # x_right = x_left + size_x - 10  # right bound
        # y_up = ((max_size_y - size_y) / 2) + 5  # upper bound
        # y_down = y_up + size_y - 10  # lower bound
        x_left = (max_size_x - size_x) / 2  # left bound
        x_right = x_left + size_x  # right bound
        y_up = (max_size_y - size_y) / 2  # upper bound
        y_down = y_up + size_y  # lower bound
        points = []
        for _ in range(nFOV):
            x = np.random.randint(x_left, x_right)
            y = np.random.randint(y_up, y_down)
            points.append((x, y))
        return points


class FOVPoints(QGraphicsItem):
    def __init__(
        self,
        x: int,
        y: int,
        size_x: float,
        size_y: float,
        mode: str,
        max_size_x: float,
        max_size_y: float,
    ):
        super().__init__()

        self._x = x
        self._y = y

        self._size_x = size_x
        self._size_y = size_y

        self._mode = mode

        self.width = max_size_x
        self.height = max_size_y

        self.point = QRectF(self._x, self._y, self._size_x, self._size_y)

    def boundingRect(self):
        return self.point

    def paint(self, painter=None, style=None, widget=None):
        x, y = self.getCenter()
        pen = QPen()
        pen.setWidth(5)
        painter.setPen(pen)
        painter.drawPoint(x, y)

    def getCenter(self):
        if self._mode == "Random":
            xc = round(self._x + (self._size_x / 2))
            yc = round(self._y + (self._size_y / 2))
        elif self._mode == "Center":
            xc = round(self._x)
            yc = round(self._y)
        return xc, yc

    def getPositionsInfo(self):
        xc, yc = self.getCenter()
        return xc, yc, self.width, self.height


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    win = SelectFOV()
    win._load_plate_info(10, 10, True)
    win.show()
    sys.exit(app.exec_())
