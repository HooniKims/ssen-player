"""Update state and real Qt controls; all release/download fixtures are deliberately synthetic."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from PySide6.QtCore import QSettings, Qt, QThread, QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox, QDialog
from app import VERSION
from app.updater import (UpdateController, fetch_release, plain_notes, load_config,
                         launch_installer, download, installation_mode)
from app.player import Player
from test_playlist import LockedAuth

REPO = load_config()['feed_url'].split('/releases/')[0]


def release(version='9.9.9'):
    return dict(version=version, notes='- 자막을 끌어 놓아 적용합니다.\n- 업데이트 상태를 함께 확인합니다.',
                size=175_000_000, zip_size=250_000_000, sha256='0'*64,
                url=f'{REPO}/releases/download/v{version}/SsenPlayer-Setup-{version}.exe',
                page=f'{REPO}/releases/tag/v{version}')


def immediate(work, done, progress=None):
    try: result = work(progress or (lambda *args: None))
    except Exception as error: done(None, str(error))
    else: done(result, '')


class Response:
    def __init__(self, data, url='https://api.github.com/fixture'):
        self.data, self.url = data, url
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self, size):
        data, self.data = self.data[:size], self.data[size:]
        return data


class UpdateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.settings = QSettings(str(Path(self.temp.name)/'settings.ini'), QSettings.IniFormat)
        self.fetcher = Mock(return_value=release())
        self.launcher, self.quitter, self.opener = Mock(), Mock(), Mock(return_value=True)
        self.controllers = []
        self.c = self.controller()

    def controller(self, **kwargs):
        options = dict(settings=self.settings, mode='installed', runner=immediate, fetcher=self.fetcher,
                       installer=self.launcher, quit_app=self.quitter, opener=self.opener)
        options.update(kwargs)
        c = UpdateController(**options)
        self.controllers.append(c)
        return c

    def tearDown(self):
        for c in self.controllers: c.shutdown()
        self.app.processEvents()
        self.temp.cleanup()

    def ready(self):
        content = b'QA fixture only, never a real installer'
        path = Path(self.temp.name)/'fake.exe'
        path.write_bytes(content)
        self.c.check()
        self.c.payload.update(size=len(content), sha256=hashlib.sha256(content).hexdigest())
        self.c.downloader = Mock(return_value=str(path))
        self.c.action()
        return path

    def test_latest_and_available(self):
        self.fetcher.return_value = release(VERSION)
        self.c.check()
        self.assertEqual(self.c.phase, 'current')
        self.assertFalse(self.c.dot_visible or self.c.show_notice)
        self.fetcher.return_value = release()
        self.c.check()
        self.assertEqual(self.c.phase, 'available')
        self.assertTrue(self.c.dot_visible and self.c.show_notice)
        self.assertTrue(self.c.last_checked)

    def test_dismiss_does_not_repeat_on_check_but_ready_can_notify_once(self):
        self.c.check()
        self.c.dismiss()
        self.c.check()
        self.assertTrue(self.c.dot_visible)
        self.assertFalse(self.c.show_notice)
        self.ready()
        self.assertTrue(self.c.show_notice)
        self.c.dismiss()
        self.c.check()
        self.assertFalse(self.c.show_notice)

    def test_skip_persists_and_newer_release_notifies(self):
        self.c.check()
        self.assertTrue(self.c.skip())
        c2 = self.controller()
        c2.check()
        self.assertTrue(c2.has_update)
        self.assertFalse(c2.dot_visible or c2.show_notice)
        self.fetcher.return_value = release('9.9.10')
        c2.check()
        self.assertTrue(c2.dot_visible and c2.show_notice)

    def test_skipped_release_can_still_download(self):
        self.c.check()
        self.c.skip()
        self.ready()
        self.c.downloader.assert_called_once()
        self.assertEqual(self.c.phase, 'ready')
        self.assertFalse(self.c.show_notice)

    def test_schedule_is_idempotent_and_toggle_persists(self):
        self.c.start()
        self.assertEqual(self.c.first_timer.interval(), 15000)
        self.assertEqual(self.c.repeat_timer.interval(), 14400000)
        timer_id = self.c.first_timer.timerId()
        self.c.start()
        self.assertEqual(self.c.first_timer.timerId(), timer_id)
        self.c.first_timer.stop()
        self.c._first_check()
        self.assertTrue(self.c.repeat_timer.isActive())
        self.c.set_auto_check(False)
        self.assertFalse(self.c.first_timer.isActive() or self.c.repeat_timer.isActive())
        c2 = self.controller()
        c2.start()
        self.assertFalse(c2.auto_check or c2.first_timer.isActive())
        before = self.fetcher.call_count
        c2.check()
        self.assertEqual(self.fetcher.call_count, before+1)
        c2.set_auto_check(True)
        self.assertTrue(c2.first_timer.isActive())

    def test_timer_callbacks_really_check(self):
        self.c.first_timer.setInterval(5)
        self.c.repeat_timer.setInterval(20)
        self.c.start()
        QTest.qWait(90)
        self.assertGreaterEqual(self.fetcher.call_count, 2)
        self.c.set_auto_check(False)
        before = self.fetcher.call_count
        QTest.qWait(60)
        self.assertEqual(self.fetcher.call_count, before)

    def test_network_error_keeps_known_release(self):
        self.c.check()
        payload = self.c.payload
        self.fetcher.side_effect = OSError('network unavailable')
        self.c.check()
        self.assertEqual(self.c.phase, 'error')
        self.assertIs(self.c.payload, payload)
        self.assertTrue(self.c.dot_visible)
        self.assertIn('network', self.c.error)

    def test_error_is_never_latest_without_a_successful_result(self):
        self.fetcher.side_effect = OSError('offline')
        self.c.check()
        self.assertEqual(self.c.phase, 'error')
        self.c.set_auto_check(False)
        self.assertEqual(self.c.phase, 'idle')
        c2 = self.controller()
        self.assertEqual(c2.phase, 'idle')

    def test_preferences_failure_preserves_value_and_is_visible(self):
        self.c.start()
        self.c.check()
        with patch.object(self.c.preferences.settings, 'status', return_value=QSettings.AccessError):
            self.assertFalse(self.c.set_auto_check(False))
            self.assertTrue(self.c.auto_check and self.c.first_timer.isActive())
            self.assertFalse(self.c.skip())
        self.assertEqual(self.c.skipped, '')
        self.assertEqual(self.c.phase, 'error')
        self.assertIn('저장 실패', self.c.error)
        self.assertTrue(self.c.dot_visible)
        self.assertNotEqual(self.settings.value('updates/auto_check'), False)

    def test_download_never_installs_and_needs_explicit_confirmation(self):
        self.ready()
        self.launcher.assert_not_called()
        self.quitter.assert_not_called()
        self.assertFalse(self.c.install())
        self.assertTrue(self.c.install(confirmed=True))
        self.launcher.assert_called_once()
        self.quitter.assert_called_once()
        self.assertFalse(self.c.install(confirmed=True))

    def test_install_busy_and_tampered_file_are_blocked(self):
        path = self.ready()
        self.c.busy_reason = lambda: '저장 작업 중'
        self.assertFalse(self.c.install(True))
        self.c.busy_reason = lambda: ''
        path.write_bytes(b'tampered')
        self.assertFalse(self.c.install(True))
        self.assertIsNone(self.c.installer)
        self.launcher.assert_not_called()
        self.quitter.assert_not_called()

    def test_download_failure_is_retryable(self):
        self.c.check()
        self.c.downloader = Mock(side_effect=OSError('network error'))
        self.c.action()
        self.assertEqual(self.c.phase, 'error')
        self.assertIsNone(self.c.operation)
        self.assertTrue(self.c.has_update)
        self.assertIsNone(self.c.installer)
        self.launcher.assert_not_called()

    def test_portable_and_development_only_open_official_page(self):
        for mode in ('portable', 'development'):
            c = self.controller(mode=mode, downloader=Mock(side_effect=AssertionError('must not download')))
            c.check()
            c.action()
            self.opener.assert_called_with(release()['page'])
            self.assertFalse(c.install(True))
            c.payload['page'] = 'https://evil.example/download'
            c.action()
            self.assertEqual(c.phase, 'error')
        self.launcher.assert_not_called()
        self.assertEqual(installation_mode(), 'development')
        with self.assertRaises(RuntimeError): launch_installer('fake.exe')

    def test_inflight_checks_and_downloads_are_not_duplicated(self):
        pending = []
        self.c.runner = lambda *args: pending.append(args)
        self.c.check()
        self.c.check()
        self.assertEqual(len(pending), 1)
        pending.pop()[1](release(), '')
        self.c.action()
        self.c.action()
        self.c.check()
        self.assertEqual(len(pending), 1)
        pending[0][2](40, 100)
        self.assertEqual(self.c.progress, 40)

    def test_real_worker_completes_on_ui_thread(self):
        c = self.controller(runner=None)
        threads = []
        c.changed.connect(lambda: threads.append(QThread.currentThread()))
        c.check()
        for _ in range(40):
            QTest.qWait(20)
            if not c.operation: break
        self.assertEqual(c.phase, 'available')
        self.assertTrue(all(thread == self.app.thread() for thread in threads))

    def test_fetch_release_uses_real_metadata_and_rejects_prerelease_mismatch(self):
        payload = release()
        data = dict(draft=False, prerelease=False, tag_name='v9.9.9', body='<b>Actual notes</b>', assets=[
            dict(browser_download_url=payload['url'], size=payload['size']),
            dict(name='SsenPlayer-9.9.9-win-x64.zip', size=220_000_000)])
        def fetch():
            with patch('app.updater.fetch_manifest', return_value=payload), patch('urllib.request.urlopen',
                return_value=Response(json.dumps(data).encode())):
                return fetch_release(load_config())
        result = fetch()
        self.assertEqual(result['notes'], 'Actual notes')
        self.assertEqual(result['zip_size'], 220_000_000)
        data['prerelease'] = True
        with self.assertRaises(ValueError): fetch()
        data['prerelease'] = False
        data['assets'][0]['size'] = 1
        with self.assertRaises(ValueError): fetch()

    def test_html_and_extreme_notes_are_bounded(self):
        text = plain_notes('<script>alert(1)</script><img src="https://evil">' + '가'*50000)
        self.assertLessEqual(len(text), 6000)
        self.assertNotIn('<img', text)

    def test_cancelled_download_does_not_leave_installer(self):
        payload = release()
        with patch('urllib.request.urlopen', return_value=Response(b'fixture')):
            with self.assertRaises(InterruptedError): download(payload, cancelled=lambda: True)


class UpdateUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
        cls.app = QApplication.instance() or QApplication([])
        from app.style import STYLE
        cls.app.setStyleSheet(STYLE)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.w = Player(QSettings(str(Path(self.temp.name)/'ui.ini'), QSettings.IniFormat), auth_factory=LockedAuth)
        self.c = self.w.updates
        self.c.mode, self.c.runner, self.c.fetcher = 'installed', immediate, lambda: release()
        self.w.show()
        self.c.check()
        QTest.qWait(20)

    def tearDown(self):
        self.w.close()
        self.w.deleteLater()
        self.app.processEvents()
        self.temp.cleanup()

    def test_version_keyboard_details_and_escape(self):
        self.assertTrue(self.w.version_button.dot)
        self.w.version_button.setFocus()
        QTest.keyClick(self.w.version_button, Qt.Key_Space)
        self.assertTrue(self.w.update_ui.dialog.isVisible())
        self.assertIn(VERSION, self.w.version_button.accessibleName())
        QTest.keyClick(self.w.update_ui.dialog, Qt.Key_Escape)
        self.assertFalse(self.w.update_ui.dialog.isVisible())

    def test_later_x_navigation_and_ready_notification(self):
        ui = self.w.update_ui
        self.assertTrue(ui.card.isVisible())
        QTest.mouseClick(ui.card.later, Qt.LeftButton)
        self.assertFalse(ui.card.isVisible())
        self.assertTrue(self.w.version_button.dot)
        self.w.set_mode('classroom')
        self.w.set_mode('window')
        self.c.check()
        QTest.qWait(20)
        self.assertFalse(ui.card.isVisible())
        self.c._downloaded(str(Path(self.temp.name)/'fake.exe'), '')
        self.assertTrue(ui.card.isVisible())
        self.assertEqual(ui.card.action.text(), '재시작하여 설치')
        QTest.mouseClick(ui.card.close_button, Qt.LeftButton)
        self.c.check()
        self.assertFalse(ui.card.isVisible())

    def test_dialog_shares_preferences_and_renders_plain_text(self):
        self.c.payload['notes'] = '&lt;img src=x onerror=alert(1)&gt;\n' + '긴 설명 '*5000
        self.w.check_update()
        d = self.w.update_ui.dialog
        self.assertEqual(d.notes.textFormat(), Qt.PlainText)
        self.assertLessEqual(len(d.notes.text()), 6000)
        d.scroll.ensureWidgetVisible(d.auto)
        self.app.processEvents()
        QTest.mouseClick(d.auto, Qt.LeftButton, pos=QPoint(10, d.auto.height()//2))
        self.assertFalse(self.c.auto_check)
        d.scroll.ensureWidgetVisible(d.check)
        QTest.mouseClick(d.check, Qt.LeftButton)
        self.assertEqual(self.c.phase, 'available')
        d.scroll.ensureWidgetVisible(d.skip)
        QTest.mouseClick(d.skip, Qt.LeftButton)
        self.assertFalse(self.w.version_button.dot or self.w.update_ui.card.isVisible())
        self.assertTrue(d.action.isEnabled())

    def test_busy_policy_and_cancelled_confirmation(self):
        self.c.installer = str(Path(self.temp.name)/'fake.exe')
        self.c.installer_launcher = Mock()
        self.w.jobs.add('capture')
        self.w.update_ui.act()
        self.assertIn('작업', self.c.error)
        self.w.jobs.clear()
        self.w.canvas.drawing = True
        self.assertTrue(self.w.update_busy_reason())
        self.w.canvas.drawing = False
        dialog = QDialog(self.w)
        dialog.busy = True
        self.assertTrue(self.w.update_busy_reason())
        dialog.busy = False
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Cancel): self.w.update_ui.act()
        self.c.installer_launcher.assert_not_called()

    def test_minimum_window_card_and_dialog_fit(self):
        self.w.resize(1024, 700)
        self.c.payload['notes'] = '\n'.join('- ' + '긴 실제 릴리스 설명 '*30 for _ in range(3))
        self.c.changed.emit()
        QTest.qWait(30)
        card = self.w.update_ui.card
        self.assertTrue(self.w.rect().contains(card.geometry()))
        self.w.check_update()
        d = self.w.update_ui.dialog
        QTest.qWait(30)
        self.assertLessEqual(d.height(), self.w.height())
        self.assertEqual(d.scroll.horizontalScrollBar().maximum(), 0)
        self.assertTrue(d.scroll.verticalScrollBar().maximum() > 0)


if __name__ == '__main__': unittest.main()
