"""Capture real Qt UI with synthetic releases, isolated settings and NO real installation."""
import hashlib
import json
import sys
import tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'tests'))
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from app.player import Player
from app import VERSION
from app.style import STYLE
from app.updater import fetch_release, load_config
from test_updates import release, immediate, LockedAuth


def main():
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = QApplication([])
    app.setStyle('Fusion')
    app.setStyleSheet(STYLE)
    output = ROOT/'artifacts/qa/updates'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        w = Player(QSettings(str(Path(temp)/'settings.ini'), QSettings.IniFormat), auth_factory=LockedAuth)
        c = w.updates
        c.mode, c.runner, c.fetcher = 'installed', immediate, lambda: release()
        w.show()
        w.auth_changed(LockedAuth.snapshot)
        c.check()
        def capture(name, widget=w):
            QTest.qWait(180)
            assert widget.grab().save(str(output/(name+'.png')))
        try:
            capture('card-normal')
            capture('version-dot', w.version_button)
            QTest.mouseClick(w.version_button, Qt.LeftButton)
            d = w.update_ui.dialog
            capture('details-normal', d)
            d.reject()
            w.resize(1024, 700)
            capture('card-minimum')
            assert w.rect().contains(w.update_ui.card.geometry())
            w.check_update()
            capture('details-minimum', d)
            assert d.scroll.horizontalScrollBar().maximum() == 0
            d.scroll.verticalScrollBar().setValue(d.scroll.verticalScrollBar().maximum())
            capture('details-minimum-bottom', d)
            d.reject()
            QTest.mouseClick(w.update_ui.card.later, Qt.LeftButton)
            c.check()
            assert not w.update_ui.card.isVisible() and w.version_button.dot
            fixture = Path(temp)/'fake-installer.exe'
            fixture.write_bytes(b'synthetic UI fixture; not executable')
            c.payload.update(size=fixture.stat().st_size, sha256=hashlib.sha256(fixture.read_bytes()).hexdigest())
            c.downloader = lambda *args: str(fixture)
            launched = []
            c.installer_launcher = launched.append
            pending = []
            c.runner = lambda *args: pending.append(args)
            c.action()
            assert c.phase == 'downloading'
            pending[0][2](43, 100)
            capture('card-downloading')
            w.check_update()
            d.scroll.verticalScrollBar().setValue(0)
            capture('details-downloading', d)
            assert d.progress.isVisible() and d.progress.value() == 43
            d.reject()
            pending[0][1](str(fixture), '')
            c.runner = immediate
            assert c.phase == 'ready' and not launched
            capture('card-ready')
            c.dismiss()
            c.check()
            assert not w.update_ui.card.isVisible()
            c._discard_installer()
            c.mode = 'portable'
            c.dismissed.clear()
            c.phase = 'available'
            c.changed.emit()
            capture('card-portable')
            assert w.update_ui.card.action.text() == '새 ZIP 받기'
            c.fail('확인 실패: 테스트용 네트워크 오류입니다. 이전에 확인한 새 버전 정보를 유지합니다.')
            w.check_update()
            d.scroll.verticalScrollBar().setValue(0)
            capture('details-error', d)
            c.payload['notes'] = '<img src=x onerror=alert(1)>\n' + '아주 긴 릴리스 설명 '*2000
            c.changed.emit()
            capture('details-untrusted-notes', d)
            assert d.notes.textFormat() == Qt.PlainText and len(d.notes.text()) <= 6000
            d.reject()
            report = dict(synthetic_release=True, synthetic_download=True, actual_installation=False,
                          card_and_dot=True, details=True, minimum_window=[1024,700],
                          dismiss_does_not_repeat=True, ready_notifies_once=True,
                          portable=True, plain_bounded_notes=True)
            live = fetch_release(load_config())
            report['live_metadata'] = {key: live[key] for key in ('version', 'size', 'zip_size', 'page')}
            report['live_installer_downloaded'] = False
            c.payload, c.phase, c.error = release(VERSION), 'current', ''
            c.changed.emit()
            assert not w.version_button.dot and not w.update_ui.card.isVisible()
            capture('latest-no-notice')
            (output/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), 'utf-8')
            print(json.dumps(report, ensure_ascii=False))
        finally:
            w.close()
            w.deleteLater()
            app.processEvents()


if __name__ == '__main__': main()
