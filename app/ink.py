"""Scene-coordinate ink: the same paths are used on screen and in captures."""
from dataclasses import dataclass, field
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainterPath, QPainterPathStroker, QPen


@dataclass
class Stroke:
    color: str
    width: float
    marker: bool = False
    points: list = field(default_factory=list)
    _cached_path: object = field(default=None, init=False, repr=False)
    _cached_count: int = field(default=0, init=False, repr=False)

    def add_point(self, point):
        if self._cached_path is not None and self._cached_count == len(self.points) and self.points:
            self._cached_path.lineTo(QPointF(*point))
            self._cached_count += 1
        self.points.append(point)

    def path(self):
        if self._cached_path is not None and self._cached_count == len(self.points):
            return self._cached_path
        path = QPainterPath()
        if self.points:
            path.moveTo(QPointF(*self.points[0]))
            if len(self.points) == 1:
                path.lineTo(QPointF(self.points[0][0] + .01, self.points[0][1]))
            for point in self.points[1:]:
                path.lineTo(QPointF(*point))
        self._cached_path = path
        self._cached_count = len(self.points)
        return path

    def pen(self):
        color = QColor(self.color)
        if self.marker:
            color.setAlpha(85)
        return QPen(color, self.width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)

    def hits(self, point, radius=14):
        stroker = QPainterPathStroker()
        stroker.setWidth(self.width + radius * 2)
        stroker.setCapStyle(Qt.RoundCap)
        return stroker.createStroke(self.path()).contains(point)


class Ink:
    def __init__(self):
        self.strokes = []
        self.history = []
        self.redo_stack = []

    def checkpoint(self):
        self.history.append(list(self.strokes))
        self.history = self.history[-100:]
        self.redo_stack.clear()

    def undo(self):
        if self.history:
            self.redo_stack.append(list(self.strokes))
            self.strokes = self.history.pop()

    def redo(self):
        if self.redo_stack:
            self.history.append(list(self.strokes))
            self.strokes = self.redo_stack.pop()

    def clear(self):
        if self.strokes:
            self.checkpoint()
            self.strokes = []

    def paint(self, painter):
        for stroke in self.strokes:
            painter.setPen(stroke.pen())
            painter.drawPath(stroke.path())
