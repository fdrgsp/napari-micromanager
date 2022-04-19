import math
import random

import numpy as np
from qtpy.QtCore import QRectF, Qt
from qtpy.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

AlignCenter = Qt.AlignmentFlag.AlignCenter


class SelectFOV(QWidget):
    """
    well_plate_info must contain:
      - well_size_x
      - well_size_y
      - is_circular: bool
    """

    def __init__(self, well_plate_info: list):
        super().__init__()

        self._size_x, self._size_y, self._is_circular = well_plate_info

        self._create_widget()

        if self._is_circular:
            self.plate_area_y.setEnabled(False)

        self._on_random_button_pressed()

    def _create_widget(self):

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)
        self.setLayout(main_layout)

        left_wdg = QWidget()
        left_wdg.setMinimumWidth(220)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        left_wdg.setLayout(layout)

        fov_label = QLabel()
        fov_label.setText("Selection mode:")
        self.FOV_selection_mode_combo = QComboBox()
        self.FOV_selection_mode_combo.addItems(["Random", "Centered"])
        self.FOV_selection_mode_combo.currentTextChanged.connect(
            self._on_FOV_selection_changed
        )
        mode = self._make_QHBoxLayout_wdg_with_label(
            fov_label, self.FOV_selection_mode_combo
        )
        layout.addWidget(mode)

        self.plate_area_label_x = QLabel()
        self.plate_area_label_x.setText("Area FOV x (mm):")
        self.plate_area_x = QDoubleSpinBox()
        self.plate_area_x.setAlignment(AlignCenter)
        self.plate_area_x.setMinimum(1)
        self.plate_area_x.setMaximum(self._size_x)
        self.plate_area_x.setValue(self._size_x)
        self.plate_area_x.valueChanged.connect(self._on_area_x_changed)
        _plate_area_x = self._make_QHBoxLayout_wdg_with_label(
            self.plate_area_label_x, self.plate_area_x
        )
        layout.addWidget(_plate_area_x)

        self.plate_area_label_y = QLabel()
        self.plate_area_label_y.setText("Area FOV y (mm):")
        self.plate_area_y = QDoubleSpinBox()
        self.plate_area_y.setAlignment(AlignCenter)
        self.plate_area_y.setMinimum(1)
        self.plate_area_y.setMaximum(self._size_y)
        self.plate_area_y.setValue(self._size_y)
        self.plate_area_y.valueChanged.connect(self._on_area_y_changed)
        _plate_area_y = self._make_QHBoxLayout_wdg_with_label(
            self.plate_area_label_y, self.plate_area_y
        )
        layout.addWidget(_plate_area_y)

        number_of_FOV_label = QLabel()
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

        self.random_button = QPushButton(text="Random")
        self.random_button.clicked.connect(self._on_random_button_pressed)
        layout.addWidget(self.random_button)

        main_layout.addWidget(left_wdg)

        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene, self)
        self.view.setStyleSheet("background:grey;")
        self.view.setFixedSize(200, 150)

        main_layout.addWidget(self.view)

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

    def _on_random_button_pressed(self):

        self.scene.clear()
        mode = self.FOV_selection_mode_combo.currentText()
        nFOV = self.number_of_FOV.value()
        area_x = self.plate_area_x.value()
        area_y = self.plate_area_y.value()
        self._set_FOV_and_mode(nFOV, mode, area_x, area_y)

    def _set_FOV_and_mode(self, nFOV: int, mode: str, area_x: float, area_y: float):

        max_size_y = 140

        if self._is_circular:
            self.scene.addEllipse(0, 0, max_size_y, max_size_y)

            if mode == "Centered":
                center_x, center_y = ((max_size_y / 2) - 2.5, (max_size_y / 2) - 2.5)
                self.scene.addEllipse(center_x, center_y, 5, 5)
                print(center_x, center_y)

            elif mode == "Random":
                diameter = (max_size_y * area_x) / self._size_x
                center = (max_size_y - diameter) / 2

                fov_area = QRectF(center, center, diameter, diameter)
                self.scene.addEllipse(fov_area)

                points = self._random_points_in_circle(nFOV, diameter, center)
                for p in points:
                    self.scene.addEllipse(p[0], p[1], 5, 5)
                    print(p)

        else:
            max_size_x = 140 if self._size_x == self._size_y else 190

            self.scene.addRect(0, 0, max_size_x, max_size_y)

            if mode == "Centered":
                center_x, center_y = ((max_size_x / 2) - 2.5, (max_size_y / 2) - 2.5)
                self.scene.addEllipse(center_x, center_y, 5, 5)
                print(center_x, center_y)

            elif mode == "Random":
                size_x = (max_size_x * area_x) / self._size_x
                size_y = (max_size_y * area_y) / self._size_y
                center_x = (max_size_x - size_x) / 2
                center_y = (max_size_y - size_y) / 2

                fov_area = QRectF(center_x, center_y, size_x, size_y)
                self.scene.addRect(fov_area)

                points = self._random_points_in_square(
                    nFOV, size_x, size_y, max_size_x, max_size_y
                )
                for p in points:
                    self.scene.addEllipse(p[0], p[1], 5, 5)
                    print(p)

    def _random_points_in_circle(self, nFOV, diameter: float, center):
        points = []
        radius = diameter / 2
        for _ in range(nFOV):
            # random angle
            alpha = 2 * math.pi * random.random()
            # random radius
            r = (radius - 5) * math.sqrt(random.random())  # -5 because of point size
            # calculating coordinates
            x = r * math.cos(alpha) + center + radius
            y = r * math.sin(alpha) + center + radius
            points.append((x, y))
        return points

    def _random_points_in_square(self, nFOV, size_x, size_y, max_size_x, max_size_y):
        x_left = ((max_size_x - size_x) / 2) + 5  # left bound
        x_right = x_left + size_x - 10  # right bound
        y_up = ((max_size_y - size_y) / 2) + 5  # upper bound
        y_down = y_up + size_y - 10  # lower bound
        points = []
        for _ in range(nFOV):
            x = np.random.randint(x_left, x_right)
            y = np.random.randint(y_up, y_down)
            points.append((x, y))
        return points


if __name__ == "__main__":
    import sys

    info = [10, 10, False]
    app = QApplication(sys.argv)
    win = SelectFOV(info)
    win.show()
    sys.exit(app.exec_())


# import math
# import random

# import matplotlib.pyplot as plt
# import numpy as np

# circlular = True
# # circlular = False

# # well diameter
# well_size_x = 15
# well_size_y = 15
# # radius of the circle
# area_size_x = 13
# area_size_y = 13
# # center of the circle (x, y)
# center_x = 0
# center_y = 0
# # number of points
# n_points = 10

# fig, ax = plt.subplots()

# if circlular:
#     well_circle = plt.Circle((0, 0), well_size_x, color="m", fill=False)
#     circle = plt.Circle((0, 0), area_size_x, color="m", fill=False)
#     ax.add_patch(well_circle)
#     ax.add_patch(circle)

#     for _ in range(n_points):
#         # random angle
#         alpha = 2 * math.pi * random.random()
#         # random radius
#         r = area_size_x * math.sqrt(random.random())
#         # calculating coordinates
#         x = r * math.cos(alpha) + center_x
#         y = r * math.sin(alpha) + center_y

#         # print("Random point", (x, y))
#         ax.plot(x, y, marker="o", markersize=10, color="k")


# else:
#     well_square = plt.Rectangle(
#         (-well_size_x, well_size_y),
#         well_size_x * 2,
#         -well_size_y * 2,
#         color="g",
#         fill=False,
#     )
#     square = plt.Rectangle(
#         (-area_size_x, area_size_y),
#         area_size_x * 2,
#         -area_size_y * 2,
#         color="g",
#         fill=False,
#     )
#     ax.add_patch(well_square)
#     ax.add_patch(square)

#     a = area_size_x  # upper bound
#     b = -area_size_x  # lower bound
#     # Random coordinates [b,a) uniform distributed
#     coordy = (b - a) * np.random.random_sample((n_points,)) + a  # generate random y
#     coordx = (b - a) * np.random.random_sample((n_points,)) + a  # generate random x

#     for i in range(len(coordx)):
#         ax.plot(coordx[i], coordy[i], marker="o", markersize=10, color="b")

# plt.show()
