"""Render the family-style vector mark into runtime and Windows icon assets."""
from pathlib import Path
from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

ROOT = Path(__file__).resolve().parent.parent
import re
import io
svg = (ROOT / 'assets/icon.svg').read_text('utf-8')

def render(size):
    source = re.sub(r'<path id="sparkle"[^>]*/>', '', svg) if size <= 32 else svg
    renderer = QSvgRenderer(source.encode('utf-8'))
    if not renderer.isValid(): raise ValueError('Invalid icon SVG')
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    renderer.render(painter)
    painter.end()
    from PySide6.QtCore import QBuffer, QIODevice
    buffer = QBuffer()
    buffer.open(QIODevice.WriteOnly)
    image.save(buffer, 'PNG')
    return Image.open(io.BytesIO(bytes(buffer.data()))).convert('RGBA')

render(512).save(ROOT/'assets/icon.png')
render(256).save(ROOT/'assets/icon-256.png')
frames = [render(size) for size in (16,24,32,48,64,128,256)]
frames[-1].save(ROOT/'assets/icon.ico',sizes=[f.size for f in frames],append_images=frames[:-1])
