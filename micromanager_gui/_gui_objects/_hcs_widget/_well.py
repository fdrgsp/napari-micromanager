import string

from qtpy.QtCore import QRectF, Qt
from qtpy.QtGui import QBrush, QColor, QFont, QPen, QTextOption
from qtpy.QtWidgets import QGraphicsItem

ALPHABET = string.ascii_uppercase


class Well(QGraphicsItem):
    def __init__(
        self,
        x: int,
        y: int,
        size_x: float,
        size_y: float,
        row: int,
        col: int,
        text_size: int,
        circular: bool,
        text_color: str = "",
    ):
        super().__init__()

        self._x = x
        self._y = y

        self._size_x = size_x
        self._size_y = size_y

        self._row = row
        self._col = col
        self._text_size = text_size
        self.circular = circular

        self.text_color = text_color

        self.brush = QBrush(Qt.green)
        self.pen = QPen(Qt.black)
        self.well_shape = QRectF(self._x, self._y, self._size_x, self._size_y)

        self.setFlag(self.ItemIsSelectable, True)

    def boundingRect(self):
        return self.well_shape

    def paint(self, painter=None, style=None, widget=None):
        painter.setBrush(self.brush)
        painter.setPen(self.pen)
        if self.circular:
            painter.drawEllipse(self.well_shape)
        else:
            painter.drawRect(self.well_shape)

        font = QFont("Helvetica", self._text_size)
        font.setWeight(QFont.Bold)
        pen = QPen(QColor(self.text_color))
        painter.setPen(pen)
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
        well = f"{ALPHABET[self._row]}{self._col + 1}"
        return well, row, col
