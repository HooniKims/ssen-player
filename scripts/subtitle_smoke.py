"""Real video, drop events and subtitle rendering with isolated, locked auth."""
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PySide6.QtCore import QObject, QMimeData, QPoint, QPointF, QSettings, Qt, QUrl, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from app.player import Player
from app.style import STYLE


class LockedAuth(QObject):
    changed = Signal(dict)
    snapshot = {'ready': True, 'canEdit': False}
    def authorize(self): return False
    def shutdown(self): pass


def main():
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = QApplication([])
    app.setStyle('Fusion')
    app.setStyleSheet(STYLE)
    output = ROOT/'artifacts/qa/subtitles'
    output.mkdir(parents=True, exist_ok=True)
    temporary = tempfile.TemporaryDirectory()
    settings = QSettings(str(Path(temporary.name)/'settings.ini'), QSettings.IniFormat)
    window = Player(settings, auth_factory=LockedAuth)
    window.show()

    def wait(condition):
        deadline = time.monotonic() + 15
        while not condition():
            assert time.monotonic() < deadline, 'Playback timed out'
            QTest.qWait(30)

    def drop(path):
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(path))])
        target = window.canvas.viewport()
        enter = QDragEnterEvent(QPoint(100, 100), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
        app.sendEvent(target, enter)
        event = QDropEvent(QPointF(100, 100), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
        app.sendEvent(target, event)
        assert enter.isAccepted() and event.isAccepted()

    try:
        media = ROOT/'artifacts/test-media/classroom.mov'
        window.add_files([str(media)])
        wait(lambda: window.media.position() > 1000 and window.canvas.video.videoSink().videoFrame().isValid())
        window.media.pause()
        QTest.qWait(100)
        paused = window.media.position()
        subtitle = Path(temporary.name)/'한글 자막.SRT'
        subtitle.write_text('1\n00:00:00,000 --> 00:01:00,000\n영상과 함께 보는 한글 자막\n드래그해서 바로 적용합니다.\n', encoding='utf-8')
        drop(subtitle)
        QTest.qWait(100)
        assert window.media.position() == paused
        assert window.canvas.subtitle == '영상과 함께 보는 한글 자막\n드래그해서 바로 적용합니다.'
        assert window.queue == [str(media.resolve())]
        window.grab().save(str(output/'window.png'))
        for mode in ('classroom', 'pure'):
            window.set_mode(mode)
            QTest.qWait(150)
            assert window.canvas.subtitle_visible
            window.grab().save(str(output/f'{mode}.png'))
        window.set_mode('window')
        window.resize(1024, 700)
        QTest.qWait(150)
        window.grab().save(str(output/'minimum-window.png'))
        window.media.play()
        wait(lambda: window.media.position() > paused + 200)
        before = window.media.position()
        drop(subtitle)
        wait(lambda: window.media.position() > before + 200)
        assert window.current == str(media.resolve())
        report = dict(real_video=True, drop_applied=True, paused_position_preserved=True,
                      playback_continues=True, subtitle_not_in_queue=True,
                      window_and_fullscreen_subtitles=True)
        (output/'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(report))
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()
        temporary.cleanup()


if __name__ == '__main__':
    main()
