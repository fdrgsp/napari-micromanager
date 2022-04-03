from pathlib import Path

import yaml
from qtpy.QtWidgets import (
    QApplication,
    QComboBox,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from micromanager_gui._gui_objects._hcs_widget._graphics_scene import GraphicsScene
from micromanager_gui._gui_objects._hcs_widget._well import Well
from micromanager_gui._gui_objects._hcs_widget._well_plate_database import WellPlate

PLATE_DATABASE = Path(__file__).parent / "_well_plate.yaml"


class MainWidget(QWidget):
    def __init__(self):
        super().__init__()

        self._create_main_wdg()

    def _create_main_wdg(self):
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(10, 0, 10, 0)
        self.setLayout(layout)
        self.scene = GraphicsScene()
        self.view = QGraphicsView(self.scene, self)
        self.view.setMinimumSize(400, 260)

        # well plate selector combo and clear selection QPushButton
        upper_wdg = QWidget()
        upper_wdg_layout = QHBoxLayout()
        wp_combo_wdg = self._create_wp_combo_selector()
        clear_button = QPushButton(text="Clear Selection")
        clear_button.clicked.connect(self.scene._clear_selection)
        calibrate_button = QPushButton(text="Calibrate Stage")
        upper_wdg_layout.addWidget(wp_combo_wdg)
        upper_wdg_layout.addWidget(clear_button)
        upper_wdg_layout.addWidget(calibrate_button)
        upper_wdg.setLayout(upper_wdg_layout)

        # add widgets
        self.layout().addWidget(upper_wdg)
        self.layout().addWidget(self.view)

        plates = self._plates_names_from_database()
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
        with open(PLATE_DATABASE) as file:
            return list(yaml.safe_load(file))

    def _get_combo_values(self) -> list:
        return [self.wp_combo.itemText(i) for i in range(self.wp_combo.count())]

    def _on_combo_changed(self, value: str):

        self.scene.clear()
        self._draw_well_plate(value)

    def _draw_well_plate(self, well_plate: str):
        current_wp_combo_items = self._get_combo_values()
        wp = WellPlate.set_format(well_plate)
        plates = self._plates_names_from_database()
        if set(plates) != set(current_wp_combo_items):
            self.wp_combo.clear()
            self.wp_combo.addItems(plates)

        max_w = 350
        max_h = 240
        size_y = max_h / wp.rows
        size_x = size_y if wp.circular else (max_w / wp.cols)
        text_size = size_y / 2.5

        width = size_x * wp.cols

        if width != self.scene.width() and self.scene.width() > 0:
            start_x = (self.scene.width() - width) / 2
            print(start_x)
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
                    Well(x, y, size_x, size_y, row, col, text_size, circular)
                )
                x += size_x
            y += size_y
            x = start_x


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    win = MainWidget()
    win.show()
    sys.exit(app.exec_())
