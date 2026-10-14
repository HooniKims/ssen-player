"""Real YouTube end events and mixed playlist playback, with isolated settings."""
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.player import Player
from app.style import STYLE
from PySide6.QtCore import QObject, QSettings, Qt, Signal, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QPlainTextEdit, QPushButton
from PySide6.QtTest import QTest


class LockedAuth(QObject):
    changed = Signal(dict)
    snapshot = {'ready': True, 'canEdit': False}
    def authorize(self): return False
    def shutdown(self): pass


QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
app = QApplication([])
app.setStyle('Fusion')
app.setStyleSheet(STYLE)
out = ROOT/'artifacts/qa/playlist-1.2.0'
out.mkdir(parents=True, exist_ok=True)
temporary = tempfile.TemporaryDirectory()
window = Player(QSettings(str(Path(temporary.name)/'settings.ini'), QSettings.IniFormat),
                auth_factory=LockedAuth)
window.show()
window.auth_changed(LockedAuth.snapshot)
report = {}


def wait(condition, seconds=45):
    deadline = time.monotonic()+seconds
    while not condition():
        if time.monotonic() > deadline:
            raise AssertionError('Timed out: '+str(window.youtube.state if window.youtube else {}))
        QTest.qWait(100)


try:
    def fill_dialog():
        dialog = window.findChild(QDialog)
        dialog.findChild(QPlainTextEdit).setPlainText('https://youtu.be/M7lc1UVf-VE\nhttps://youtu.be/aqz-KE-bpKQ')
        dialog.grab().save(str(out/'add-links.png'))
        next(b for b in dialog.findChildren(QPushButton) if b.text() == '목록에 추가').click()
    QTimer.singleShot(250, fill_dialog)
    window.open_youtube_links()
    assert len(window.queue) == 2 and window.current is None
    report['dialog_add_without_autoplay'] = True
    urls = list(window.queue)
    local = str(ROOT/'artifacts/test-media/classroom.mov')
    window.add_files([local])
    window.load(urls[0])
    wait(lambda: window.youtube.state.get('time', 0) > 1)
    window.grab().save(str(out/'playlist.png'))
    window.youtube.command('seek', window.youtube.state['duration']-1)
    wait(lambda: window.current == urls[1])
    report['youtube_auto_next'] = True
    wait(lambda: window.youtube.state.get('time', 0) > 1)
    window.youtube.command('seek', window.youtube.state['duration']-1)
    wait(lambda: window.source_kind == 'local' and window.media.position() > 100)
    report['youtube_to_local'] = True
    window.move_queue_item(-1)
    window.media.setPosition(window.media.duration()-400)
    wait(lambda: window.current == urls[1])
    report['local_to_youtube'] = True
    report['passed'] = True
except Exception as error:
    report['error'] = str(error)
    window.grab().save(str(out/'failure.png'))
finally:
    (out/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), 'utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    window.close()
    app.processEvents()
    temporary.cleanup()
assert report.get('passed'), report
