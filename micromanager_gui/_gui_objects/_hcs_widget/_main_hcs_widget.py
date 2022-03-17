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

# from ._plate import Plate
# from ._graphics_scene import GraphicsScene
from micromanager_gui._gui_objects._hcs_widget._plate import Plate


class MainWidget(QWidget):
    def __init__(self):
        super().__init__()

        self._create_main_wdg()

    def _create_main_wdg(self):
        # QGraphicsScene and QGraphicsView
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

        self._draw_well_plate(6)

    def _create_wp_combo_selector(self):
        combo_wdg = QWidget()
        wp_combo_layout = QHBoxLayout()
        wp_combo_layout.setContentsMargins(0, 0, 0, 0)
        wp_combo_layout.setSpacing(3)

        combo_label = QLabel()
        combo_label.setText("Well Plate:")
        combo_label.setMaximumWidth(75)

        wp_combo = QComboBox()
        wp_combo.setGeometry(215, 10, 100, 100)
        items = ["6", "12", "24", "48", "96", "Custom"]
        wp_combo.addItems(items)
        wp_combo.currentTextChanged.connect(self._on_combo_changed)

        wp_combo_layout.addWidget(combo_label)
        wp_combo_layout.addWidget(wp_combo)
        combo_wdg.setLayout(wp_combo_layout)

        return combo_wdg

    def _on_combo_changed(self, value: str):

        if value == "Custom":
            print("Not yet implemented!")
            return

        self.scene.clear()
        self._draw_well_plate(int(value))

    def _get_draw_parameters(self, wells: int):
        if wells == 6:
            rows = 2
            cols = 3
            dm = 115
            text_size = 20
        elif wells == 12:
            rows = 3
            cols = 4
            dm = 75
            text_size = 18
        elif wells == 24:
            rows = 4
            cols = 6
            dm = 55
            text_size = 16
        elif wells == 48:
            rows = 6
            cols = 8
            dm = 35
            text_size = 14
        elif wells == 96:
            rows = 8
            cols = 12
            dm = 25
            text_size = 10

        return rows, cols, dm, text_size

    def _draw_well_plate(self, wells: int):
        rows, cols, dm, text_size = self._get_draw_parameters(wells)
        self._create_well_plate(rows, cols, dm, text_size, wells)

    def _create_well_plate(
        self, rows: int, cols: int, dm: int, text_size: int, wells: int
    ):
        x, y, gap = (25, 5, 5) if wells in {12, 48} else (5, 5, 5)
        for row in range(rows):
            for col in range(cols):
                self.scene.addItem(Plate(x, y, dm, row, col, text_size))
                x += dm + gap
            y += dm + gap
            x = 25 if wells in {12, 48} else 5

        # height = 5 + (dm * rows) + (gap * (rows - 1))
        # width = 5 + (dm * cols) + (gap * (cols - 1))
        # print(f'width: {width}, height: {height}')


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    win = MainWidget()
    win.show()
    sys.exit(app.exec_())
