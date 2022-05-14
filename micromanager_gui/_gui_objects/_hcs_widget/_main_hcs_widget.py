from pathlib import Path
from typing import Optional, Tuple

import yaml
from fonticon_mdi6 import MDI6
from pymmcore_plus import CMMCorePlus
from pymmcore_plus.mda import PMDAEngine
from qtpy.QtCore import QSize, Qt
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
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from superqt.fonticon import icon
from superqt.utils import signals_blocked
from useq import MDASequence

from micromanager_gui._core import get_core_singleton
from micromanager_gui._gui_objects._hcs_widget._calibration_widget import (
    PlateCalibration,
)
from micromanager_gui._gui_objects._hcs_widget._channel_and_position_widget import (
    ChannelPositionWidget,
)
from micromanager_gui._gui_objects._hcs_widget._generate_FOV import SelectFOV
from micromanager_gui._gui_objects._hcs_widget._graphics_items import FOVPoints, Well
from micromanager_gui._gui_objects._hcs_widget._graphics_scene import GraphicsScene
from micromanager_gui._gui_objects._hcs_widget._update_yaml import UpdateYaml
from micromanager_gui._gui_objects._hcs_widget._well_plate_database import WellPlate
from micromanager_gui._mda import SEQUENCE_META, SequenceMeta

PLATE_DATABASE = Path(__file__).parent / "_well_plate.yaml"
AlignCenter = Qt.AlignmentFlag.AlignCenter


class HCSWidget(QWidget):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        mmcore: Optional[CMMCorePlus] = None,
    ):
        super().__init__(parent)

        self._mmc = mmcore or get_core_singleton()
        self._mmc.mda.events.sequenceStarted.connect(self._on_mda_started)
        self._mmc.mda.events.sequenceFinished.connect(self._on_mda_finished)
        self._mmc.mda.events.sequencePauseToggled.connect(self._on_mda_paused)
        self._mmc.events.mdaEngineRegistered.connect(self._update_mda_engine)

        self.wp = None

        self._create_main_wdg()

        self._update_wp_combo()

    def _create_main_wdg(self):  # sourcery skip: class-extract-method

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setAlignment(AlignCenter)
        widgets = self._add_tab_wdg()
        scroll.setWidget(widgets)

        layout.addWidget(scroll)

        btns = self._create_btns_wdg()
        layout.addWidget(btns)

    def _add_tab_wdg(self):

        tab = QTabWidget()
        tab.setTabPosition(QTabWidget.West)

        select_plate_tab = self._create_plate_and_fov_tab()
        self.ch_and_pos_list = ChannelPositionWidget()
        self.ch_and_pos_list.position_list_button.clicked.connect(
            self._generate_pos_list
        )
        self.saving_tab = QWidget()

        tab.addTab(select_plate_tab, "  Plate, FOVs and Calibration  ")
        tab.addTab(self.ch_and_pos_list, "  Channel and Positions List  ")
        tab.addTab(self.saving_tab, "  Saving  ")

        return tab

    def _create_plate_and_fov_tab(self):
        wdg = QWidget()
        wdg_layout = QVBoxLayout()
        wdg_layout.setSpacing(20)
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

        # add widgets
        view_group = QGroupBox("Plate Selection")
        view_gp_layout = QVBoxLayout()
        view_gp_layout.setSpacing(0)
        view_gp_layout.setContentsMargins(10, 10, 10, 10)
        view_group.setLayout(view_gp_layout)
        view_gp_layout.addWidget(upper_wdg)
        view_gp_layout.addWidget(self.view)
        wdg_layout.addWidget(view_group)

        FOV_group = QGroupBox(title="FOVs Selection")
        FOV_group.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        FOV_gp_layout = QVBoxLayout()
        FOV_gp_layout.setSpacing(0)
        FOV_gp_layout.setContentsMargins(10, 10, 10, 10)
        FOV_group.setLayout(FOV_gp_layout)
        FOV_gp_layout.addWidget(self.FOV_selector)
        wdg_layout.addWidget(FOV_group)

        cal_group = QGroupBox(title="Plate Calibration")
        cal_group_layout = QVBoxLayout()
        cal_group_layout.setSpacing(0)
        cal_group_layout.setContentsMargins(10, 10, 10, 10)
        cal_group.setLayout(cal_group_layout)
        self.calibration = PlateCalibration()
        self.calibration.PlateFromCalibration.connect(self._on_plate_from_calobration)
        cal_group_layout.addWidget(self.calibration)
        wdg_layout.addWidget(cal_group)

        verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        wdg_layout.addItem(verticalSpacer)

        return wdg

    def _create_btns_wdg(self):

        wdg = QWidget()
        wdg.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed))
        wdg_layout = QHBoxLayout()
        wdg_layout.setAlignment(Qt.AlignVCenter)
        wdg_layout.setSpacing(10)
        wdg_layout.setContentsMargins(10, 15, 10, 10)
        wdg.setLayout(wdg_layout)

        acq_wdg = QWidget()
        acq_wdg_layout = QHBoxLayout()
        acq_wdg_layout.setSpacing(0)
        acq_wdg_layout.setContentsMargins(0, 0, 0, 0)
        acq_wdg.setLayout(acq_wdg_layout)
        acquisition_order_label = QLabel(text="Acquisition Order:")
        lbl_sizepolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        acquisition_order_label.setSizePolicy(lbl_sizepolicy)
        self.acquisition_order_comboBox = QComboBox()
        self.acquisition_order_comboBox.setMinimumWidth(100)
        self.acquisition_order_comboBox.addItems(["tpzc", "tpcz", "ptzc", "ptcz"])
        acq_wdg_layout.addWidget(acquisition_order_label)
        acq_wdg_layout.addWidget(self.acquisition_order_comboBox)

        btn_sizepolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        min_width = 100
        icon_size = 40
        self.run_Button = QPushButton(text="Run")
        self.run_Button.clicked.connect(self._on_run_clicked)
        self.run_Button.setMinimumWidth(min_width)
        self.run_Button.setStyleSheet("QPushButton { text-align: center; }")
        self.run_Button.setSizePolicy(btn_sizepolicy)
        self.run_Button.setIcon(icon(MDI6.play_circle_outline, color=(0, 255, 0)))
        self.run_Button.setIconSize(QSize(icon_size, icon_size))
        self.pause_Button = QPushButton("Pause")
        self.pause_Button.released.connect(lambda: self._mmc.mda.toggle_pause())
        self.pause_Button.setMinimumWidth(min_width)
        self.pause_Button.setStyleSheet("QPushButton { text-align: center; }")
        self.pause_Button.setSizePolicy(btn_sizepolicy)
        self.pause_Button.setIcon(icon(MDI6.pause_circle_outline, color="green"))
        self.pause_Button.setIconSize(QSize(icon_size, icon_size))
        self.pause_Button.hide()
        self.cancel_Button = QPushButton("Cancel")
        self.cancel_Button.released.connect(lambda: self._mmc.mda.cancel())
        self.cancel_Button.setMinimumWidth(min_width)
        self.cancel_Button.setStyleSheet("QPushButton { text-align: center; }")
        self.cancel_Button.setSizePolicy(btn_sizepolicy)
        self.cancel_Button.setIcon(icon(MDI6.stop_circle_outline, color="magenta"))
        self.cancel_Button.setIconSize(QSize(icon_size, icon_size))
        self.cancel_Button.hide()

        spacer = QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Expanding)

        wdg_layout.addWidget(acq_wdg)
        wdg_layout.addItem(spacer)
        wdg_layout.addWidget(self.run_Button)
        wdg_layout.addWidget(self.pause_Button)
        wdg_layout.addWidget(self.cancel_Button)

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
        self.calibration._update_gui(value)

    def _on_plate_from_calobration(self, coords: Tuple):
        x_list = [x[0] for x in [*coords]]
        y_list = [y[1] for y in [*coords]]
        x_max, x_min = (max(x_list), min(x_list))
        y_max, y_min = (max(y_list), min(y_list))

        width_mm = (abs(x_max) + abs(x_min)) / 1000
        height_mm = (abs(y_max) + abs(y_min)) / 1000

        with open(PLATE_DATABASE) as file:
            f = yaml.safe_load(file)
            f.pop("_from calibration")

        with open(PLATE_DATABASE, "w") as file:
            new = {
                "_from calibration": {
                    "circular": False,
                    "id": "_from calibration",
                    "cols": 1,
                    "rows": 1,
                    "well_size_x": width_mm,
                    "well_size_y": height_mm,
                    "well_spacing_x": 0,
                    "well_spacing_y": 0,
                }
            }
            f.update(new)
            yaml.dump(f, file)

        self.scene.clear()
        self._draw_well_plate("_from calibration")

    def _draw_well_plate(self, well_plate: str):
        self.wp = WellPlate.set_format(well_plate)

        max_w = self._width - 10
        max_h = self._height - 10
        size_y = max_h / self.wp.rows
        size_x = (
            size_y
            if self.wp.circular or self.wp.well_size_x == self.wp.well_size_y
            else (max_w / self.wp.cols)
        )
        text_size = size_y / 2.3

        width = size_x * self.wp.cols

        if width != self.scene.width() and self.scene.width() > 0:
            start_x = (self.scene.width() - width) / 2
            start_x = max(start_x, 0)
        else:
            start_x = 0

        self._create_well_plate(
            self.wp.rows,
            self.wp.cols,
            start_x,
            size_x,
            size_y,
            text_size,
            self.wp.circular,
        )

        self.FOV_selector._load_plate_info(
            self.wp.well_size_x, self.wp.well_size_y, self.wp.circular
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
            value = list(new_plate.keys())[0]
            self.wp_combo.setCurrentText(value)
            self._on_combo_changed(value)
        else:
            items = [self.wp_combo.itemText(i) for i in range(self.wp_combo.count())]
            self.wp_combo.setCurrentText(items[0])
            self._on_combo_changed(items[0])

    def _generate_pos_list(self):

        if not self.calibration.is_calibrated:
            raise ValueError("Plate not calibrated! Calibrate it first.")

        if not self._mmc.getPixelSizeUm():
            raise ValueError("Pixel Size not defined! Set pixel size first.")

        well_list = self.scene._get_plate_positions()

        if not well_list:
            raise ValueError("No Well selected! Select at least one well first.")

        self.ch_and_pos_list.clear_positions()

        plate_info = self.wp.getAllInfo()

        # center stage coords of calibrated well a1
        a1_x = self.calibration.A1_well[1]
        a1_y = self.calibration.A1_well[2]

        # distance between wells from plate database (mm)
        x_step, y_step = plate_info.get("well_distance")

        cal_well_list = []
        for pos in well_list:
            well, row, col = pos
            # find center stage coords for all the selected wells
            if well == "A1":
                x = a1_x
                y = a1_y
            else:
                x = a1_x + ((x_step * 1000) * col)
                y = a1_y + ((y_step * 1000) * row)
            cal_well_list.append((well, x, y))

        fovs = [
            item.getPositionsInfo()
            for item in self.FOV_selector.scene.items()
            if isinstance(item, FOVPoints)
        ]

        row = 0

        # center coord in px (of QGraphicsView))
        cx = 100
        cy = 100

        for pos in cal_well_list:
            well_name, cx_cal, cy_cal = pos

            # well dimensions from database (mm)
            well_x, well_y = plate_info.get("well_size")
            # well dimensions from database (um)
            well_x_um = well_x * 1000
            well_y_um = well_y * 1000

            for idx, fov in enumerate(fovs):

                # pixel coord fx and fy + pixel width and height drawing
                fx, fy, w, h = fov

                # find 1 px value in um depending on well dimension
                px_val_x = well_x_um / w
                px_val_y = well_y_um / h

                # shift point coords in px when center is (0, 0)
                new_fx = fx - cx
                new_fy = fy - cy

                # find stage coords of fov point
                new_fx_cal = cx_cal + (new_fx * px_val_x)
                new_fy_cal = cy_cal + (new_fy * px_val_y)

                self._add_to_table(row, well_name, idx, new_fx_cal, new_fy_cal)

                row += 1

    def _add_to_table(self, row, well_name, idx, new_fx_cal, new_fy_cal):
        self._add_position_row()
        name = QTableWidgetItem(f"{well_name}_pos{idx:03d}")
        name.setTextAlignment(int(Qt.AlignHCenter | Qt.AlignVCenter))
        self.ch_and_pos_list.stage_tableWidget.setItem(row, 0, name)
        stage_x = QTableWidgetItem(str(new_fx_cal))
        stage_x.setTextAlignment(int(Qt.AlignHCenter | Qt.AlignVCenter))
        self.ch_and_pos_list.stage_tableWidget.setItem(row, 1, stage_x)
        stage_y = QTableWidgetItem(str(new_fy_cal))
        stage_y.setTextAlignment(int(Qt.AlignHCenter | Qt.AlignVCenter))
        self.ch_and_pos_list.stage_tableWidget.setItem(row, 2, stage_y)

        if self.ch_and_pos_list.z_combo.currentText() != "None":
            selected_z_stage = self.ch_and_pos_list.z_combo.currentText()
            z_pos = self._mmc.getPosition(selected_z_stage)
            item = QTableWidgetItem(str(z_pos))
            item.setTextAlignment(int(Qt.AlignHCenter | Qt.AlignVCenter))
            self.ch_and_pos_list.stage_tableWidget.setItem(row, 3, item)

    def _add_position_row(self) -> int:
        idx = self.ch_and_pos_list.stage_tableWidget.rowCount()
        self.ch_and_pos_list.stage_tableWidget.insertRow(idx)
        return idx

    def get_state(self) -> dict:
        ch_table = self.ch_and_pos_list.channel_tableWidget
        state = {
            "axis_order": self.acquisition_order_comboBox.currentText(),
            "channels": [
                {
                    "config": ch_table.cellWidget(c, 0).currentText(),
                    "group": self._mmc.getChannelGroup() or "Channel",
                    "exposure": ch_table.cellWidget(c, 1).value(),
                }
                for c in range(ch_table.rowCount())
            ],
            "time_plan": None,
            "z_plan": None,
            "stage_positions": [],
        }

        if self.ch_and_pos_list.time_group.isChecked():
            unit = {"min": "minutes", "sec": "seconds", "ms": "milliseconds"}[
                self.ch_and_pos_list.time_comboBox.currentText()
            ]
            state["time_plan"] = {
                "interval": {unit: self.ch_and_pos_list.interval_spinBox.value()},
                "loops": self.ch_and_pos_list.timepoints_spinBox.value(),
            }

        if self.ch_and_pos_list.stack_group.isChecked():

            if self.ch_and_pos_list.z_tabWidget.currentIndex() == 0:
                state["z_plan"] = {
                    "range": self.ch_and_pos_list.zrange_spinBox.value(),
                    "step": self.ch_and_pos_list.step_size_doubleSpinBox.value(),
                }
            elif self.ch_and_pos_list.z_tabWidget.currentIndex() == 1:
                state["z_plan"] = {
                    "above": self.ch_and_pos_list.above_doubleSpinBox.value(),
                    "below": self.ch_and_pos_list.below_doubleSpinBox.value(),
                    "step": self.ch_and_pos_list.step_size_doubleSpinBox.value(),
                }

        for r in range(self.ch_and_pos_list.stage_tableWidget.rowCount()):
            pos = {
                "x": float(self.ch_and_pos_list.stage_tableWidget.item(r, 1).text()),
                "y": float(self.ch_and_pos_list.stage_tableWidget.item(r, 2).text()),
            }
            if self.ch_and_pos_list.z_combo.currentText() != "None":
                pos["z"] = float(
                    self.ch_and_pos_list.stage_tableWidget.item(r, 3).text()
                )
            state["stage_positions"].append(pos)

        return MDASequence(**state)

    def _update_mda_engine(self, newEngine: PMDAEngine, oldEngine: PMDAEngine):
        oldEngine.events.sequenceStarted.disconnect(self._on_mda_started)
        oldEngine.events.sequenceFinished.disconnect(self._on_mda_finished)
        oldEngine.events.sequencePauseToggled.disconnect(self._on_mda_paused)

        newEngine.events.sequenceStarted.connect(self._on_mda_started)
        newEngine.events.sequenceFinished.connect(self._on_mda_finished)
        newEngine.events.sequencePauseToggled.connect(self._on_mda_paused)

    def _on_mda_started(self, sequence):
        self.pause_Button.show()
        self.cancel_Button.show()
        self.run_Button.hide()

    def _on_mda_paused(self, paused):
        self.pause_Button.setText("Go" if paused else "Pause")

    def _on_mda_finished(self, sequence):
        self.pause_Button.hide()
        self.cancel_Button.hide()
        self.run_Button.show()

    def _on_run_clicked(self):

        if len(self._mmc.getLoadedDevices()) < 2:
            raise ValueError("Load a cfg file first.")

        if self.ch_and_pos_list.channel_tableWidget.rowCount() <= 0:
            raise ValueError("Select at least one channel.")

        if self.ch_and_pos_list.stage_tableWidget.rowCount() <= 0:
            raise ValueError("Select at least one position.")

        # if self.save_groupBox.isChecked() and not (
        #     self.fname_lineEdit.text() and Path(self.dir_lineEdit.text()).is_dir()
        # ):
        #     raise ValueError("Select a filename and a valid directory.")

        experiment = self.get_state()

        SEQUENCE_META[experiment] = SequenceMeta(
            mode="hca",
            split_channels=False,
            should_save=False,
            file_name="",
            save_dir="",
            save_pos=False,
        )
        self._mmc.run_mda(experiment)  # run the MDA experiment asynchronously
        return


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    win = HCSWidget()
    win.show()
    sys.exit(app.exec_())
