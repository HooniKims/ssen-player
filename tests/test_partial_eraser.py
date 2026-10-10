import unittest

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QImage, QPainter

from app.ink import Ink, Stroke


class PartialEraserTests(unittest.TestCase):
    def test_swept_erase_and_history(self):
        ink = Ink()
        original = Stroke('#ff0000', 10, points=[(10, 50), (190, 50)])
        ink.strokes = [original]
        ink.checkpoint()
        ink.erase_area(QPointF(100, 0), QPointF(100, 100), 12)
        shape = ink.strokes[0].shape()
        self.assertFalse(shape.contains(QPointF(100, 50)))
        self.assertTrue(shape.contains(QPointF(50, 50)))
        self.assertTrue(shape.contains(QPointF(150, 50)))
        self.assertFalse(ink.strokes[0].hits(QPointF(100, 50), 1))
        self.assertTrue(ink.strokes[0].hits(QPointF(150, 50), 1))
        ink.undo()
        self.assertIs(ink.strokes[0], original)
        ink.redo()
        self.assertFalse(ink.strokes[0].shape().contains(QPointF(100, 50)))

    def test_marker_partial_width_and_render(self):
        ink = Ink()
        ink.strokes = [Stroke('#ff0000', 40, True, [(10, 50), (190, 50)])]
        ink.erase_area(QPointF(100, 36), QPointF(100, 36), 8)
        image = QImage(200, 100, QImage.Format_ARGB32)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        ink.paint(painter)
        painter.end()
        self.assertEqual(image.pixelColor(100, 36).alpha(), 0)
        self.assertEqual(image.pixelColor(100, 55).alpha(), 85)
        self.assertEqual(image.pixelColor(50, 50).alpha(), 85)

    def test_dot_removal_and_miss(self):
        ink = Ink()
        dot = Stroke('#ffffff', 6, points=[(50, 50)])
        ink.strokes = [dot]
        ink.erase_area(QPointF(150, 50), QPointF(150, 50), 12)
        self.assertIs(ink.strokes[0], dot)
        ink.erase_area(QPointF(50, 50), QPointF(50, 50), 12)
        self.assertEqual(ink.strokes, [])
