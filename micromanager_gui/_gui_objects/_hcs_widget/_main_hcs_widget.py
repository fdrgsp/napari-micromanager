from pathlib import Path
from typing import Optional

import yaml
from qtpy.QtWidgets import (
    QApplication,
    QComboBox,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)
from superqt.utils import signals_blocked

from micromanager_gui._gui_objects._hcs_widget._graphics_scene import GraphicsScene
from micromanager_gui._gui_objects._hcs_widget._update_yaml import UpdateYaml
from micromanager_gui._gui_objects._hcs_widget._well import Well
from micromanager_gui._gui_objects._hcs_widget._well_plate_database import WellPlate

PLATE_DATABASE = Path(__file__).parent / "_well_plate.yaml"


class HCSWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._create_main_wdg()

    def _create_main_wdg(self):
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(10, 0, 10, 0)
        self.setLayout(layout)
        self.scene = GraphicsScene()
        self.view = QGraphicsView(self.scene, self)
        self.view.setStyleSheet("background:grey;")
        self.view.setMinimumSize(400, 260)

        # well plate selector combo and clear selection QPushButton
        upper_wdg = QWidget()
        upper_wdg_layout = QHBoxLayout()
        wp_combo_wdg = self._create_wp_combo_selector()
        custom_plate = QPushButton(text="Custom Plate")
        custom_plate.clicked.connect(self._update_plate_yaml)
        clear_button = QPushButton(text="Clear Selection")
        clear_button.clicked.connect(self.scene._clear_selection)
        upper_wdg_layout.addWidget(wp_combo_wdg)
        upper_wdg_layout.addWidget(custom_plate)
        upper_wdg_layout.addWidget(clear_button)
        upper_wdg.setLayout(upper_wdg_layout)

        calibrate_button = QPushButton(text="Calibrate Stage")

        # add widgets
        self.layout().addWidget(upper_wdg)
        self.layout().addWidget(self.view)
        self.layout().addWidget(calibrate_button)

        verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.layout().addItem(verticalSpacer)

        self._update_wp_combo()

    def _update_wp_combo(self):
        plates = self._plates_names_from_database()
        plates.sort()
        self.wp_combo.clear()
        self.wp_combo.addItems(plates)

    def _create_wp_combo_selector(self):
        combo_wdg = QWidget()
        wp_combo_layout = QHBoxLayout()
        wp_combo_layout.setContentsMargins(0, 0, 0, 0)
        wp_combo_layout.setSpacing(3)

        combo_label = QLabel()
        combo_label.setText("Well Plate:")
        combo_label.setMaximumWidth(75)

        self.wp_combo = QComboBox()
        self.wp_combo.setGeometry(215, 10, 100, 100)
        self.wp_combo.currentTextChanged.connect(self._on_combo_changed)

        wp_combo_layout.addWidget(combo_label)
        wp_combo_layout.addWidget(self.wp_combo)
        combo_wdg.setLayout(wp_combo_layout)

        return combo_wdg

    def _plates_names_from_database(self) -> list:
        with open(
            PLATE_DATABASE,
        ) as file:
            return list(yaml.safe_load(file))

    def _on_combo_changed(self, value: str):
        print(value)
        self.scene.clear()
        self._draw_well_plate(value)
        print("draw")

    def _draw_well_plate(self, well_plate: str):
        wp = WellPlate.set_format(well_plate)

        max_w = 350
        max_h = 240
        size_y = max_h / wp.rows
        size_x = size_y if wp.circular else (max_w / wp.cols)
        text_size = size_y / 2.5

        width = size_x * wp.cols

        if width != self.scene.width() and self.scene.width() > 0:
            start_x = (self.scene.width() - width) / 2
        else:
            start_x = 0

        self._create_well_plate(
            wp.rows, wp.cols, start_x, size_x, size_y, text_size, wp.circular
        )

    def _create_well_plate(
        self,
        rows: int,
        cols: int,
        start_x: int,
        size_x: int,
        size_y: int,
        text_size: int,
        circular: bool,
    ):
        x = start_x
        y = 0
        for row in range(rows):
            for col in range(cols):
                self.scene.addItem(
                    Well(x, y, size_x, size_y, row, col, text_size, circular, "gray")
                )
                x += size_x
            y += size_y
            x = start_x

    def _update_plate_yaml(self):
        self.plate = UpdateYaml(self)
        self.plate.yaml_updated.connect(
            self._update_wp_combo_from_yaml
        )  # UpdateYaml() signal
        self.plate.show()
        self._clear_values()

    def _clear_values(self):
        self.plate._circular_checkbox.setChecked(False),
        self.plate._id.setText(""),
        self.plate._cols.setValue(0),
        self.plate._rows.setValue(0),
        self.plate._well_size_x.setValue(0.0),
        self.plate._well_size_y.setValue(0.0),
        self.plate._well_spacing_x.setValue(0.0),
        self.plate._well_spacing_y.setValue(0.0)

    def _update_wp_combo_from_yaml(self, new_plate):
        plates = self._plates_names_from_database()
        plates.sort()
        with signals_blocked(self.wp_combo):
            self.wp_combo.clear()
            self.wp_combo.addItems(plates)
        if new_plate:
            self.wp_combo.setCurrentText(list(new_plate.keys())[0])
        else:
            items = [self.wp_combo.itemText(i) for i in range(self.wp_combo.count())]
            self.wp_combo.setCurrentText(items[0])
            self._draw_well_plate(items[0])


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    win = HCSWidget()
    win.show()
    sys.exit(app.exec_())
