import string

from qtpy.QtCore import QRectF, Qt
from qtpy.QtGui import QBrush, QColor, QFont, QTextOption
from qtpy.QtWidgets import QGraphicsItem

ALPHABET = string.ascii_uppercase


class Plate(QGraphicsItem):
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
