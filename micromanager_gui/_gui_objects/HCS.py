import string

from qtpy.QtCore import QRect, QRectF, Qt
from qtpy.QtGui import QBrush, QColor, QFont, QTextOption, QTransform
from qtpy.QtWidgets import (
    QApplication,
    QComboBox,
    QGraphicsItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRubberBand,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

ALPHABET = string.ascii_uppercase


class GraphicsScene(QGraphicsScene):
    def __init__(self):
        super().__init__()

        self.unselected = QBrush(Qt.green)
        self.selected = QBrush(Qt.magenta)

        self.ellipse_pos = 0
        self.new_ellipse_pos = 0

        self._selected_wells = []

    def mousePressEvent(self, event):
        self.originQPoint = event.screenPos()
        self.currentQRubberBand = QRubberBand(QRubberBand.Rectangle)
        self.originCropPoint = event.scenePos()

        self._selected_wells = [item for item in self.items() if item.isSelected()]
        for item in self._selected_wells:
            item.setBrush(self.selected)

        if ellipse := self.itemAt(self.originCropPoint, QTransform()):
            if ellipse.isSelected():
                ellipse.setBrush(self.unselected)
                ellipse.setSelected(False)
            else:
                ellipse.setBrush(self.selected)
                ellipse.setSelected(True)

    def mouseMoveEvent(self, event):
        self.currentQRubberBand.setGeometry(QRect(self.originQPoint, event.screenPos()))
        self.currentQRubberBand.show()
        selection = self.items(QRectF(self.originCropPoint, event.scenePos()))
        for item in self.items():
            if item in selection:
                item.setBrush(self.selected)
                item.setSelected(True)
            elif item not in self._selected_wells:
                item.setBrush(self.unselected)
                item.setSelected(False)

    def mouseReleaseEvent(self, event):
        self.currentQRubberBand.hide()
        self._print_selected_wells()  # to be removed

    def _clear_selection(self):
        """clear selection"""
        for item in self.items():
            if item.isSelected():
                item.setSelected(False)
                item.setBrush(self.unselected)
        self._print_selected_wells()  # to be removed

    def _print_selected_wells(self):  # to be removed
        print("___________")
        print("Selected wells:")
        selected_wells = [item.getPos() for item in self.items() if item.isSelected()]
        selected_wells.sort()
        for i in selected_wells:
            print(i)


class MainWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.setGeometry(0, 0, 580, 320)

        self._create_wdg()

    def _create_wdg(self):

        self.setLayout(QHBoxLayout())
        self.scene = GraphicsScene()
        self.view = QGraphicsView(self.scene, self)
        self.layout().addWidget(self.view)

        combo_wdg = QWidget()
        wp_combo_layout = QHBoxLayout()
        wp_combo_layout.setContentsMargins(0, 0, 0, 0)
        wp_combo_layout.setSpacing(3)

        combo_label = QLabel()
        combo_label.setText("Well Plate:")

        wp_combo = QComboBox()
        wp_combo.setGeometry(215, 10, 100, 100)
        items = ["6", "12", "24", "48", "96"]
        wp_combo.addItems(items)
        wp_combo.currentTextChanged.connect(self._on_combo_changed)

        wp_combo_layout.addWidget(combo_label)
        wp_combo_layout.addWidget(wp_combo)
        combo_wdg.setLayout(wp_combo_layout)

        main = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        clear_button = QPushButton(text="Clear Selection")
        clear_button.clicked.connect(self.scene._clear_selection)
        calibrate_button = QPushButton(text="Calibrate Stage")
        pos_list_button = QPushButton(text="Get Position List")
        verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)

        main_layout.addWidget(combo_wdg)
        main_layout.addWidget(clear_button)
        main_layout.addWidget(calibrate_button)
        main_layout.addWidget(pos_list_button)
        main_layout.addSpacerItem(verticalSpacer)

        main.setLayout(main_layout)

        self.layout().addWidget(main)

        self._draw_well_plate(6)

    def _on_combo_changed(self, value: str):
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
                self.scene.addItem(CellPlate(x, y, dm, row, col, text_size))
                x += dm + gap
            y += dm + gap
            x = 25 if wells in {12, 48} else 5

        # height = 5 + (dm * rows) + (gap * (rows - 1))
        # width = 5 + (dm * cols) + (gap * (cols - 1))
        # print(f'width: {width}, height: {height}')


class CellPlate(QGraphicsItem):
    def __init__(self, x, y, dm, row, col, text_size):
        super().__init__()

        self._x = x
        self._y = y
        self._dm = dm
        self._row = row
        self._col = col
        self._text_size = text_size

        self.text_x = self._x + (self._dm / 2) - 8
        self.text_y = self._y + (self._dm / 2) + 5

        self.brush = QBrush(Qt.green)
        self.ellipse = QRectF(self._x, self._y, self._dm, self._dm)

        self.setFlag(self.ItemIsSelectable, True)

    def boundingRect(self):
        return self.ellipse

    def paint(self, painter=None, style=None, widget=None):
        painter.setBrush(self.brush)
        painter.drawEllipse(self.ellipse)

        font = QFont("Helvetica", self._text_size)
        font.setWeight(QFont.Bold)
        painter.setFont(font)
        well_name = f"{ALPHABET[self._row]}{self._col + 1}"
        painter.drawText(self.ellipse, well_name, QTextOption(Qt.AlignCenter))

    def setBrush(self, brush: QColor = QBrush(Qt.green)):
        self.brush = brush
        self.update()

    def getBrush(self):
        return self.brush

    def getPos(self):
        row = self._row
        col = self._col
        xc = self._x + (self._dm / 2)
        yc = self._y + (self._dm / 2)
        well = f"{ALPHABET[self._row]}{self._col + 1}"
        return well, row, col, xc, yc


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    win = MainWidget()
    win.show()
    sys.exit(app.exec_())
