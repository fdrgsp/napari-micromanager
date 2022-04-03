import string

from qtpy.QtCore import QRectF, Qt
from qtpy.QtGui import QBrush, QColor, QFont, QTextOption
from qtpy.QtWidgets import QGraphicsItem

ALPHABET = string.ascii_uppercase


class Well(QGraphicsItem):
    # def __init__(self, x, y, dm, row, col, text_size, circular):
    def __init__(self, x, y, size_x, size_y, row, col, text_size, circular):
        super().__init__()

        self._x = x
        self._y = y
        # self._dm = dm

        self._size_x = size_x
        self._size_y = size_y

        self._row = row
        self._col = col
        self._text_size = text_size
        self.circular = circular

        self.text_x = self._x + (self._size_x / 2) - 8
        self.text_y = self._y + (self._size_x / 2) + 5
        # self.text_x = self._x + (self._dm / 2) - 8
        # self.text_y = self._y + (self._dm / 2) + 5

        self.brush = QBrush(Qt.green)
        self.well_shape = QRectF(self._x, self._y, self._size_x, self._size_y)

        self.setFlag(self.ItemIsSelectable, True)

    def boundingRect(self):
        return self.well_shape

    def paint(self, painter=None, style=None, widget=None):
        painter.setBrush(self.brush)
        if self.circular:
            painter.drawEllipse(self.well_shape)
        else:
            painter.drawRect(self.well_shape)

        font = QFont("Helvetica", self._text_size)
        font.setWeight(QFont.Bold)
        painter.setFont(font)
        well_name = f"{ALPHABET[self._row]}{self._col + 1}"
        painter.drawText(self.well_shape, well_name, QTextOption(Qt.AlignCenter))

    def setBrush(self, brush: QColor = QBrush(Qt.green)):
        self.brush = brush
        self.update()

    def getBrush(self):
        return self.brush

    def getPos(self):
        row = self._row
        col = self._col
        xc = self._x + (self._size_x / 2)
        yc = self._y + (self._size_y / 2)
        well = f"{ALPHABET[self._row]}{self._col + 1}"
        return well, row, col, xc, yc
