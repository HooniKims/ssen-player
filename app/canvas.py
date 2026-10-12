from PySide6.QtCore import Qt, QRectF, QPointF, QSizeF, Signal, QEvent
from PySide6.QtGui import QColor, QPainter, QImage, QFont, QPen
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene
from PySide6.QtMultimediaWidgets import QGraphicsVideoItem
from PySide6.QtMultimedia import QVideoFrame
from .ink import Ink, Stroke

WIDTH, HEIGHT = 1920, 1080


def paint_frame(frame, painter):
    options = QVideoFrame.PaintOptions()
    options.aspectRatioMode = Qt.KeepAspectRatio
    options.backgroundColor = QColor('#111d19')
    options.paintFlags = QVideoFrame.PaintOptions.PaintFlag.DontDrawSubtitles
    frame.paint(painter, QRectF(0, 0, WIDTH, HEIGHT), options)


class VideoItem(QGraphicsVideoItem):
    def paint(self, painter, option, widget=None):
        frame = self.videoSink().videoFrame()
        if frame.isValid():
            paint_frame(frame, painter)


class Canvas(QGraphicsView):
    togglePlayback = Signal()
    fullscreenRequested = Signal()
    inkChanged = Signal()

    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(0, 0, WIDTH, HEIGHT, self))
        self.video = VideoItem()
        self.video.setSize(QSizeF(WIDTH, HEIGHT))
        self.scene().addItem(self.video)
        self.setBackgroundBrush(QColor('#FFFFFF'))
        self.setFrameShape(QGraphicsView.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setRenderHint(QPainter.Antialiasing)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setAlignment(Qt.AlignCenter)
        self.viewport().setAttribute(Qt.WA_AcceptTouchEvents)
        self.viewport().setMouseTracking(True)
        self.ink = Ink()
        self.edit_guard = lambda: False
        self.tool = 'pointer'
        self.color = '#ffdf59'
        self.pen_width = 6
        self.eraser_radius = 24
        self.erase_last = None
        self.drawing = False
        self.loaded = False
        self.subtitle = ''
        self.subtitle_visible = True
        self.video.videoSink().videoFrameChanged.connect(lambda _: self.viewport().update())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)

    def drawBackground(self, painter, rect):
        painter.fillRect(rect, QColor('#111d19' if self.loaded else '#FFFFFF'))

    def set_tool(self, tool):
        self.tool = tool
        self.viewport().setCursor(Qt.ArrowCursor if tool == 'pointer' else Qt.CrossCursor)

    def drawForeground(self, painter, rect):
        painter.setRenderHint(QPainter.Antialiasing)
        if not self.loaded:
            painter.setPen(QColor('#006241'))
            painter.setFont(QFont('Hakgyoansim Jayeon R', 42))
            painter.drawText(QRectF(0, 370, WIDTH, 90), Qt.AlignCenter, '보고, 쓰고, 함께 배우다')
            painter.setFont(QFont('Malgun Gothic', 22))
            painter.setPen(QColor('#555555'))
            painter.drawText(QRectF(0, 485, WIDTH, 65), Qt.AlignCenter, '영상을 끌어 놓거나 파일 열기를 눌러 주세요')
            painter.setFont(QFont('Malgun Gothic', 17))
            painter.drawText(QRectF(0, 572, WIDTH, 50), Qt.AlignCenter, 'MOV · MP4 · MKV · AVI · WebM')
        self.paint_subtitle(painter)
        self.ink.paint(painter)

    def paint_subtitle(self, painter):
        if not self.subtitle or not self.subtitle_visible:
            return
        painter.save()
        painter.setFont(QFont('Malgun Gothic', 28, QFont.Bold))
        rect = QRectF(100, 835, WIDTH - 200, 205)
        flags = Qt.AlignHCenter | Qt.AlignBottom | Qt.TextWordWrap
        painter.setPen(QColor('#000000'))
        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
            painter.drawText(rect.translated(dx, dy), flags, self.subtitle)
        painter.setPen(QColor('white'))
        painter.drawText(rect, flags, self.subtitle)
        painter.restore()

    def stroke_begin(self, point):
        if not self.edit_guard(): return
        if self.tool == 'pointer' or not self.sceneRect().contains(point):
            return
        self.drawing = True
        self.erase_last = point
        self.ink.checkpoint()
        if self.tool not in ('eraser', 'area_eraser'):
            self.ink.strokes.append(Stroke(self.color, self.pen_width * (4 if self.tool == 'marker' else 1), self.tool == 'marker'))
        self.stroke_move(point)

    def stroke_move(self, point):
        if not self.drawing:
            return
        point = QPointF(max(0, min(WIDTH, point.x())), max(0, min(HEIGHT, point.y())))
        if self.tool == 'area_eraser':
            self.ink.erase_area(self.erase_last, point, self.eraser_radius)
            self.erase_last = point
        elif self.tool == 'eraser':
            self.ink.strokes = [s for s in self.ink.strokes if not s.hits(point)]
        elif self.ink.strokes:
            self.ink.strokes[-1].add_point((point.x(), point.y()))
        self.viewport().update()
        self.inkChanged.emit()

    def stroke_end(self, point=None):
        if not self.drawing:
            return
        if point is not None:
            self.stroke_move(point)
        self.drawing = False
        self.ink.commit()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.tool == 'pointer':
                self.togglePlayback.emit()
            else:
                self.stroke_begin(self.mapToScene(event.position().toPoint()))
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self.stroke_move(self.mapToScene(event.position().toPoint()))

    def mouseReleaseEvent(self, event):
        self.stroke_end(self.mapToScene(event.position().toPoint()))
        event.accept()

    def mouseDoubleClickEvent(self, event):
        if self.tool == 'pointer':
            self.fullscreenRequested.emit()
        event.accept()

    def viewportEvent(self, event):
        kind = event.type()
        if kind in (QEvent.TouchBegin, QEvent.TouchUpdate, QEvent.TouchEnd, QEvent.TouchCancel):
            if self.tool != 'pointer':
                points = event.points()
                if points:
                    point = self.mapToScene(points[0].position().toPoint())
                    if kind == QEvent.TouchBegin:
                        self.stroke_begin(point)
                    elif kind == QEvent.TouchUpdate:
                        self.stroke_move(point)
                    else:
                        self.stroke_end(point)
                if kind in (QEvent.TouchEnd, QEvent.TouchCancel):
                    self.stroke_end()
                event.accept()
                return True
        if kind in (QEvent.TabletPress, QEvent.TabletMove, QEvent.TabletRelease) and self.tool != 'pointer':
            point = self.mapToScene(event.position().toPoint())
            if kind == QEvent.TabletPress:
                self.stroke_begin(point)
            elif kind == QEvent.TabletMove:
                self.stroke_move(point)
            else:
                self.stroke_end(point)
            event.accept()
            return True
        return super().viewportEvent(event)

    def capture(self, width=WIDTH, height=HEIGHT):
        # Decode only on explicit capture; never copy GPU frames to CPU every frame.
        frame = self.video.videoSink().videoFrame()
        if not frame.isValid():
            raise ValueError('캡처할 영상이 없습니다. 영상을 먼저 재생해 주세요.')
        result = QImage(width, height, QImage.Format_RGB32)
        result.fill(QColor('#111d19'))
        painter = QPainter(result)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        # Recording asks for its own size directly instead of rescaling every 1080p frame.
        painter.scale(width / WIDTH, height / HEIGHT)
        # Same Qt rendering path as the screen, including MOV rotation/mirroring.
        paint_frame(frame, painter)
        self.paint_subtitle(painter)
        self.ink.paint(painter)
        painter.end()
        return result
