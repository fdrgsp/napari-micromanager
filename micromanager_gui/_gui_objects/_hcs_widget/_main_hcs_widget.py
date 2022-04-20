from pathlib import Path
from typing import Optional

import yaml
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QApplication,
    QComboBox,
    QGraphicsView,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)
from superqt.utils import signals_blocked

from micromanager_gui._gui_objects._hcs_widget._generate_FOV import FOVPoints, SelectFOV
from micromanager_gui._gui_objects._hcs_widget._graphics_scene import GraphicsScene
from micromanager_gui._gui_objects._hcs_widget._update_yaml import UpdateYaml
from micromanager_gui._gui_objects._hcs_widget._well import Well
from micromanager_gui._gui_objects._hcs_widget._well_plate_database import WellPlate

PLATE_DATABASE = Path(__file__).parent / "_well_plate.yaml"
AlignCenter = Qt.AlignmentFlag.AlignCenter


class HCSWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._create_main_wdg()

        self._update_wp_combo()

    def _create_main_wdg(self):  # sourcery skip: class-extract-method

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 10, 0, 10)
        self.setLayout(layout)

        scroll = QScrollArea()
        scroll.setAlignment(AlignCenter)
        widgets = self._view_scene_widgets()
        scroll.setWidget(widgets)
        layout.addWidget(scroll)

    def _view_scene_widgets(self):

        wdg = QWidget()
        wdg_layout = QVBoxLayout()
        wdg_layout.setSpacing(10)
        wdg_layout.setContentsMargins(10, 10, 10, 10)
        wdg.setLayout(wdg_layout)

        self.scene = GraphicsScene()
        self.view = QGraphicsView(self.scene, self)
        self.view.setStyleSheet("background:grey;")
        self._width = 500
        self._height = 300
        self.view.setMinimumSize(self._width, self._height)

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

        self.FOV_selector = SelectFOV()

        calibrate_button = QPushButton(text="Calibrate Stage")
        position_list_button = QPushButton(text="Create Positons List")
        position_list_button.clicked.connect(self._generate_pos_list)

        # add widgets
        view_group = QGroupBox()
        view_gp_layout = QVBoxLayout()
        view_gp_layout.setSpacing(0)
        view_gp_layout.setContentsMargins(10, 0, 10, 10)
        view_group.setLayout(view_gp_layout)
        view_gp_layout.addWidget(upper_wdg)
        view_gp_layout.addWidget(self.view)
        wdg_layout.addWidget(view_group)

        FOV_group = QGroupBox()
        FOV_gp_layout = QVBoxLayout()
        FOV_gp_layout.setSpacing(0)
        FOV_gp_layout.setContentsMargins(10, 10, 10, 10)
        FOV_group.setLayout(FOV_gp_layout)
        FOV_gp_layout.addWidget(self.FOV_selector)
        wdg_layout.addWidget(FOV_group)

        cfg_group = QGroupBox()
        cfg_gp_layout = QVBoxLayout()
        cfg_gp_layout.setSpacing(5)
        cfg_gp_layout.setContentsMargins(10, 10, 10, 10)
        cfg_group.setLayout(cfg_gp_layout)
        cfg_gp_layout.addWidget(calibrate_button)  # TODO: add icon
        cfg_gp_layout.addWidget(position_list_button)
        wdg_layout.addWidget(cfg_group)

        verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        wdg_layout.addItem(verticalSpacer)

        return wdg

    def _create_wp_combo_selector(self):
        combo_wdg = QWidget()
        wp_combo_layout = QHBoxLayout()
        wp_combo_layout.setContentsMargins(0, 0, 0, 0)
        wp_combo_layout.setSpacing(0)

        combo_label = QLabel()
        combo_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        combo_label.setText("Plate:")
        combo_label.setMaximumWidth(75)

        self.wp_combo = QComboBox()
        self.wp_combo.currentTextChanged.connect(self._on_combo_changed)

        wp_combo_layout.addWidget(combo_label)
        wp_combo_layout.addWidget(self.wp_combo)
        combo_wdg.setLayout(wp_combo_layout)

        return combo_wdg

    def _update_wp_combo(self):
        plates = self._plates_names_from_database()
        plates.sort()
        self.wp_combo.clear()
        self.wp_combo.addItems(plates)

    def _plates_names_from_database(self) -> list:
        with open(
            PLATE_DATABASE,
        ) as file:
            return list(yaml.safe_load(file))

    def _on_combo_changed(self, value: str):
        self.scene.clear()
        self._draw_well_plate(value)

    def _draw_well_plate(self, well_plate: str):
        wp = WellPlate.set_format(well_plate)

        max_w = self._width - 10
        max_h = self._height - 10
        size_y = max_h / wp.rows
        size_x = (
            size_y
            if wp.circular or wp.well_size_x == wp.well_size_y
            else (max_w / wp.cols)
        )
        text_size = size_y / 2.3

        width = size_x * wp.cols

        if width != self.scene.width() and self.scene.width() > 0:
            start_x = (self.scene.width() - width) / 2
            start_x = max(start_x, 0)
        else:
            start_x = 0

        self._create_well_plate(
            wp.rows, wp.cols, start_x, size_x, size_y, text_size, wp.circular
        )

        self.FOV_selector._load_plate_info(wp.well_size_x, wp.well_size_y, wp.circular)

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

    def _update_plate_yaml(self):
        self.plate = UpdateYaml(self)
        self.plate.yaml_updated.connect(
            self._update_wp_combo_from_yaml
        )  # UpdateYaml() signal
        self.plate.show()
        self._clear_values()

    def _clear_values(self):
        self.plate._circular_checkbox.setChecked(False),
        self.plate._id.setText("")
        self.plate._cols.setValue(0)
        self.plate._rows.setValue(0)
        self.plate._well_size_x.setValue(0.0)
        self.plate._well_size_y.setValue(0.0)
        self.plate._well_spacing_x.setValue(0.0)
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
            self._on_combo_changed(items[0])

    def _generate_pos_list(self):

        well_list = self.scene._get_plate_positions()

        if not well_list:
            print("select at least one well!")
            return

        well_list.sort()
        for pos in well_list:
            print(pos)
        # TODO: convert in stage coordinates after calibration

        fovs = [
            item.getCenter()
            for item in self.FOV_selector.scene.items()
            if isinstance(item, FOVPoints)
        ]
        for fov in fovs:
            print(fov)
        # TODO: convert in plate coordinates
        # TODO: convert in stage coordinates after calibration


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    win = HCSWidget()
    win.show()
    sys.exit(app.exec_())
