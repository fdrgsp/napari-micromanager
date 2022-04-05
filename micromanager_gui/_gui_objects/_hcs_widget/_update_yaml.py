from pathlib import Path
from typing import Optional

import yaml
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import (
    QApplication,
    QCheckBox,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QWidget,
)

PLATE_DATABASE = Path(__file__).parent / "_well_plate.yaml"
AlignCenter = Qt.AlignmentFlag.AlignCenter


class UpdateYaml(QWidget):

    yaml_updated = Signal(dict)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__()

        self._create_gui()

    def _create_gui(self):

        main_layout = QGridLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

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
        self._well_spacing_x.setAlignment(AlignCenter)
        main_layout.addWidget(self._well_spacing_x_label, 3, 0)
        main_layout.addWidget(self._well_spacing_x, 3, 1)

        self._well_spacing_y_label = QLabel()
        self._well_spacing_y_label.setText("y spacing:")
        self._well_spacing_y = QDoubleSpinBox()
        self._well_spacing_y.setAlignment(AlignCenter)
        main_layout.addWidget(self._well_spacing_y_label, 4, 0)
        main_layout.addWidget(self._well_spacing_y, 4, 1)

        self._well_size_x_label = QLabel()
        self._well_size_x_label.setText("well size x:")
        self._well_size_x = QDoubleSpinBox()
        self._well_size_x.setAlignment(AlignCenter)
        main_layout.addWidget(self._well_size_x_label, 5, 0)
        main_layout.addWidget(self._well_size_x, 5, 1)

        self._well_size_y_label = QLabel()
        self._well_size_y_label.setText("well size y:")
        self._well_size_y = QDoubleSpinBox()
        self._well_size_y.setAlignment(AlignCenter)
        main_layout.addWidget(self._well_size_y_label, 6, 0)
        main_layout.addWidget(self._well_size_y, 6, 1)

        self.circular_checkbox = QCheckBox(text="circular")
        main_layout.addWidget(self.circular_checkbox, 7, 0)

        btn_wdg = QWidget()
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(5, 0, 5, 0)
        btn_layout.setSpacing(5)
        self._cancel_btn = QPushButton(text="Cancel")
        self._cancel_btn.clicked.connect(self._close)
        self._ok_btn = QPushButton(text="Ok")
        self._ok_btn.clicked.connect(self._update_plate_yaml)
        btn_layout.addWidget(self._cancel_btn)
        btn_layout.addWidget(self._ok_btn)
        btn_wdg.setLayout(btn_layout)
        main_layout.addWidget(btn_wdg, 8, 0, 1, 2)

        self.setLayout(main_layout)

    def _close(self):
        self.close()

    def _update_plate_yaml(self):

        if not self._id.text():
            return

        with open(PLATE_DATABASE) as file:
            f = yaml.safe_load(file)

        with open(PLATE_DATABASE, "w") as file:
            new = {
                f"{self._id.text()}": {
                    "circular": self.circular_checkbox.isChecked(),
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

        self._close()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    win = UpdateYaml()
    win.show()
    sys.exit(app.exec_())
