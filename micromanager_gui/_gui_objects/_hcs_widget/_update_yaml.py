from pathlib import Path
from typing import Optional

import yaml
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

PLATE_DATABASE = Path(__file__).parent / "_well_plate.yaml"
AlignCenter = Qt.AlignmentFlag.AlignCenter


class UpdateYaml(QWidget):

    yaml_updated = Signal(object)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__()

        self._create_gui()

        self._update_table()

        self._update_values(1, 0)

    def _create_gui(self):

        main_layout = QGridLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        self.plate_combo = QComboBox()

        self._id_label = QLabel()
        self._id_label.setText("plate name:")
        self._id = QLineEdit()
        main_layout.addWidget(self._id_label, 0, 0)
        main_layout.addWidget(self._id, 0, 1)

        self._rows_label = QLabel()
        self._rows_label.setText("rows:")
        self._rows = QSpinBox()
        self._rows.setAlignment(AlignCenter)
        main_layout.addWidget(self._rows_label, 1, 0)
        main_layout.addWidget(self._rows, 1, 1)

        self._cols_label = QLabel()
        self._cols_label.setText("columns:")
        self._cols = QSpinBox()
        self._cols.setAlignment(AlignCenter)
        main_layout.addWidget(self._cols_label, 2, 0)
        main_layout.addWidget(self._cols, 2, 1)

        self._well_spacing_x_label = QLabel()
        self._well_spacing_x_label.setText("x spacing:")
        self._well_spacing_x = QDoubleSpinBox()
        self._well_spacing_x.setMaximum(100000.0)
        self._well_spacing_x.setAlignment(AlignCenter)
        main_layout.addWidget(self._well_spacing_x_label, 3, 0)
        main_layout.addWidget(self._well_spacing_x, 3, 1)

        self._well_spacing_y_label = QLabel()
        self._well_spacing_y_label.setText("y spacing:")
        self._well_spacing_y = QDoubleSpinBox()
        self._well_spacing_y.setMaximum(100000.0)
        self._well_spacing_y.setAlignment(AlignCenter)
        main_layout.addWidget(self._well_spacing_y_label, 4, 0)
        main_layout.addWidget(self._well_spacing_y, 4, 1)

        self._well_size_x_label = QLabel()
        self._well_size_x_label.setText("well size x:")
        self._well_size_x = QDoubleSpinBox()
        self._well_size_x.setMaximum(100000.0)
        self._well_size_x.setAlignment(AlignCenter)
        main_layout.addWidget(self._well_size_x_label, 5, 0)
        main_layout.addWidget(self._well_size_x, 5, 1)

        self._well_size_y_label = QLabel()
        self._well_size_y_label.setText("well size y:")
        self._well_size_y = QDoubleSpinBox()
        self._well_size_y.setMaximum(100000.0)
        self._well_size_y.setAlignment(AlignCenter)
        main_layout.addWidget(self._well_size_y_label, 6, 0)
        main_layout.addWidget(self._well_size_y, 6, 1)

        is_circular_label = QLabel()
        is_circular_label.setText("circular:")
        self._circular_checkbox = QCheckBox()
        main_layout.addWidget(is_circular_label, 7, 0)
        main_layout.addWidget(self._circular_checkbox, 7, 1)

        btn_wdg = QWidget()
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(5, 5, 5, 0)
        btn_layout.setSpacing(5)
        self._close_btn = QPushButton(text="Close")
        self._close_btn.clicked.connect(self._close)
        self._delete_btn = QPushButton(text="Delete")
        self._delete_btn.clicked.connect(self._delete_plate)
        self._ok_btn = QPushButton(text="Add/Update")
        self._ok_btn.clicked.connect(self._update_plate_yaml)
        btn_layout.addWidget(self._close_btn)
        btn_layout.addWidget(self._ok_btn)
        btn_layout.addWidget(self._delete_btn)
        btn_wdg.setLayout(btn_layout)
        main_layout.addWidget(btn_wdg, 8, 0, 1, 3)

        self.plate_table = QTableWidget()
        self.plate_table.horizontalHeader().setStretchLastSection(True)
        self.plate_table.verticalHeader().setVisible(False)
        self.plate_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.plate_table.setRowCount(1)
        self.plate_table.setColumnCount(1)
        self.plate_table.setHorizontalHeaderLabels(["Plate"])
        self.plate_table.cellClicked.connect(self._update_values)
        main_layout.addWidget(self.plate_table, 0, 2, 8, 1)

        self.setLayout(main_layout)

    def _plates_names_from_database(self) -> list:
        with open(
            PLATE_DATABASE,
        ) as file:
            return list(yaml.safe_load(file))

    def _update_table(self):
        plates = self._plates_names_from_database()
        self.plate_table.setRowCount(len(plates))
        for row, p in enumerate(plates):
            item = QTableWidgetItem(p)
            self.plate_table.setItem(row, 0, item)

    def _update_values(self, row: int, col: int):

        plate_name = self.plate_table.item(row, col).text()

        with open(PLATE_DATABASE) as file:
            data = yaml.safe_load(file)

            self._id.setText(data[plate_name].get("id"))
            self._rows.setValue(data[plate_name].get("rows"))
            self._cols.setValue(data[plate_name].get("cols"))
            self._well_spacing_x.setValue(data[plate_name].get("well_spacing_x"))
            self._well_spacing_y.setValue(data[plate_name].get("well_spacing_y"))
            self._well_size_x.setValue(data[plate_name].get("well_size_x"))
            self._well_size_y.setValue(data[plate_name].get("well_size_y"))
            self._circular_checkbox.setChecked(data[plate_name].get("circular"))

    def _update_plate_yaml(self):

        if not self._id.text():
            return

        with open(PLATE_DATABASE) as file:
            f = yaml.safe_load(file)

        with open(PLATE_DATABASE, "w") as file:
            new = {
                f"{self._id.text()}": {
                    "circular": self._circular_checkbox.isChecked(),
                    "id": self._id.text(),
                    "cols": self._cols.value(),
                    "rows": self._rows.value(),
                    "well_size_x": self._well_size_x.value(),
                    "well_size_y": self._well_size_y.value(),
                    "well_spacing_x": self._well_spacing_x.value(),
                    "well_spacing_y": self._well_spacing_y.value(),
                }
            }
            f.update(new)
            yaml.dump(f, file)
            self.yaml_updated.emit(new)

        self._update_table()

        match = self.plate_table.findItems(self._id.text(), Qt.MatchExactly)
        self.plate_table.item(match[0].row(), 0).setSelected(True)

    def _close(self):
        self.close()

    def _delete_plate(self):

        selected_rows = {r.row() for r in self.plate_table.selectedIndexes()}

        if not selected_rows:
            return

        plate_names = [self.plate_table.item(r, 0).text() for r in selected_rows]

        with open(PLATE_DATABASE) as file:
            f = yaml.safe_load(file)
            for plate_name in plate_names:
                f.pop(plate_name)

        with open(PLATE_DATABASE, "w") as file:
            yaml.dump(f, file)
            self.yaml_updated.emit(None)

        for plate_name in plate_names:
            match = self.plate_table.findItems(plate_name, Qt.MatchExactly)
            self.plate_table.removeRow(match[0].row())

        print("DELETE -> ", plate_names, selected_rows)


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    win = UpdateYaml()
    win.show()
    sys.exit(app.exec_())
