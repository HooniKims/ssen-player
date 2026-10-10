"""Real Qt/FFmpeg playback and ink/capture smoke test, using synthetic media."""
import os
import sys
import time
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ['QT_MEDIA_BACKEND'] = 'ffmpeg'
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings, QPoint, QPointF, Qt
from PySide6.QtGui import QFontDatabase, QImage
from PySide6.QtTest import QTest
from PySide6.QtMultimedia import QMediaPlayer
from app.player import Player
from app.style import STYLE
import psutil

start = time.perf_counter()
app = QApplication([])
app.setStyle('Fusion')
app.setStyleSheet(STYLE)
QFontDatabase.addApplicationFont(str(ROOT/'assets/Ghanachocolate.ttf'))
out = ROOT/'artifacts/qa'
out.mkdir(parents=True, exist_ok=True)
settings = QSettings(str(out/'test-settings.ini'), QSettings.IniFormat)
settings.clear()
window = Player(settings)
window.capture_dir = str(out/'captures')
window.show()
QTest.qWait(300)
report = {'window_ready_seconds': round(time.perf_counter()-start, 3)}
window.grab().save(str(out/'01-empty.png'))

def wait_until(condition, timeout=10000):
    limit = time.monotonic()+timeout/1000
    while not condition():
        if time.monotonic() > limit: raise AssertionError('Timed out')
        QTest.qWait(50)

media = str(ROOT/'artifacts/test-media/classroom.mov')
window.add_files([media])
wait_until(lambda: window.media.position() > 500)
assert not window.canvas.video.videoSink().videoFrame().toImage().isNull()
window.choose_tool('pen')
view = window.canvas
first = view.mapFromScene(QPointF(500, 300))
last = view.mapFromScene(QPointF(1300, 700))
before = window.media.position()
QTest.mousePress(view.viewport(), Qt.LeftButton, pos=first)
for i in range(1, 31):
    p = QPoint(first.x()+(last.x()-first.x())*i//30, first.y()+(last.y()-first.y())*i//30)
    QTest.mouseMove(view.viewport(), p, 12)
QTest.mouseRelease(view.viewport(), Qt.LeftButton, pos=last)
assert len(view.ink.strokes) == 1
assert len(view.ink.strokes[0].points) >= 20
QTest.qWait(200)
assert window.media.position() > before, 'Drawing paused playback'
window.capture()
wait_until(lambda: not window.jobs)
assert '완료' in window.status.text(), window.status.text()
capture = max((out/'captures').glob('*.png'), key=lambda path:path.stat().st_mtime_ns)
image = QImage(str(capture))
assert image.width() == 1920 and image.height() == 1080
color = image.pixelColor(900, 500)
assert color.red() > 240 and color.green() > 195 and color.blue() < 130, color.name()
window.grab().save(str(out/'02-playing-ink.png'))
window.media.pause()
QTest.qWait(200)
paused = window.media.position()
view.stroke_begin(QPointF(600, 500))
view.stroke_move(QPointF(1200, 500))
view.stroke_end()
window.capture()
wait_until(lambda: not window.jobs)
QTest.qWait(150)
assert window.media.position() == paused
assert len(view.ink.strokes) == 2
touch = QTest.createTouchDevice()
touch_start = view.viewport().mapTo(window, view.mapFromScene(QPointF(700, 200)))
touch_end = view.viewport().mapTo(window, view.mapFromScene(QPointF(900, 400)))
# On Windows QtTest must inject at QWindow, then Qt routes to the viewport.
touch_sequence = QTest.touchEvent(window.windowHandle(), touch)
touch_sequence.press(0, touch_start, window.windowHandle()).commit()
QTest.qWait(50)
touch_sequence.move(0, touch_end, window.windowHandle()).commit()
touch_sequence.release(0, touch_end, window.windowHandle()).commit()
QTest.qWait(50)
assert len(view.ink.strokes) == 3, f'Touch stroke count: {len(view.ink.strokes)}'
window.undo()
assert len(view.ink.strokes) == 2
window.undo()
assert len(view.ink.strokes) == 1
window.redo()
assert len(view.ink.strokes) == 2
window.set_mode('classroom')
QTest.qWait(300)
assert window.tools_scroll.isVisible()
assert not window.header.isVisible()
assert len(view.ink.strokes) == 2
window.grab().save(str(out/'03-classroom.png'))
window.set_mode('pure')
QTest.qWait(2700)
assert not window.tools_scroll.isVisible()
assert not window.footer.isVisible()
assert not window.pure_exit.isVisible()
window.grab().save(str(out/'04-pure.png'))
window.escape()
assert window.mode == 'classroom'
window.escape()
assert window.mode == 'window'
window.clear_ink()
window.undo()
assert len(view.ink.strokes) == 2
report['memory_mb_paused'] = round(psutil.Process().memory_info().rss/1024**2, 1)
report['mov_playback'] = True
report['drawing_during_playback'] = True
report['capture_contains_ink'] = True
report['capture_while_paused'] = True
report['fullscreen_modes'] = True
report['synthetic_touch_ink'] = True
report['capture_file'] = str(capture)
window.close()
Path(out/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), 'utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
