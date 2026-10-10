"""Render the family-style vector mark into runtime and Windows icon assets."""
from pathlib import Path
from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

ROOT = Path(__file__).resolve().parent.parent
renderer = QSvgRenderer(str(ROOT / 'assets/icon.svg'))
if not renderer.isValid():
    raise ValueError('Invalid icon SVG')
image = QImage(1024, 1024, QImage.Format_ARGB32)
image.fill(Qt.transparent)
painter = QPainter(image)
painter.setRenderHint(QPainter.Antialiasing)
renderer.render(painter)
painter.end()
if not image.save(str(ROOT / 'assets/icon.png')):
    raise OSError('Could not write icon PNG')
with Image.open(ROOT / 'assets/icon.png') as source:
    source.save(ROOT / 'assets/icon.ico', sizes=[(s, s) for s in (16, 20, 24, 32, 40, 48, 64, 128, 256)])
