import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QMimeData, QPoint, QPointF, QSettings, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QApplication
from app.player import Player
from app.subtitles import read_subtitles
from test_playlist import LockedAuth


class SubtitleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.window = Player(QSettings(str(self.root/'settings.ini'), QSettings.IniFormat), auth_factory=LockedAuth)
        self.video = self.root/'수업 영상.mp4'
        self.video.touch()
        self.source_patch = patch.object(self.window.media, 'setSource')
        self.play_patch = patch.object(self.window.media, 'play')
        self.source = self.source_patch.start()
        self.play = self.play_patch.start()

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()
        self.source_patch.stop()
        self.play_patch.stop()
        self.temp.cleanup()

    def subtitle(self, name='다른 이름.SRT', text='안녕하세요', encoding='utf-8'):
        path = self.root/name
        path.write_text(f'1\n00:00:01,000 --> 00:00:03,000\n{text}\n', encoding=encoding)
        return path

    def drop(self, paths, target=None):
        target = target or self.window.canvas.viewport()
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(p)) for p in paths])
        enter = QDragEnterEvent(QPoint(10, 10), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
        self.app.sendEvent(target, enter)
        self.assertTrue(enter.isAccepted())
        event = QDropEvent(QPointF(10, 10), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
        self.app.sendEvent(target, event)
        self.assertTrue(event.isAccepted())

    def test_drop_on_video_updates_immediately_without_restarting(self):
        w = self.window
        w.add_files([str(self.video)])
        self.source.reset_mock()
        self.play.reset_mock()
        w.canvas.subtitle_visible = False
        w.subtitle_delay = 9000
        with patch.object(w.media, 'position', return_value=1500):
            self.drop([self.subtitle()])
        self.assertEqual(w.canvas.subtitle, '안녕하세요')
        self.assertTrue(w.canvas.subtitle_visible)
        self.assertEqual(w.subtitle_delay, 0)
        self.assertEqual(w.queue, [str(self.video)])
        self.assertEqual(w.current, str(self.video))
        self.source.assert_not_called()
        self.play.assert_not_called()
        w.position(3500)
        self.assertEqual(w.canvas.subtitle, '')

    def test_video_and_subtitle_drop_in_either_order(self):
        for reverse in (False, True):
            with self.subTest(reverse=reverse):
                paths = [self.video, self.subtitle()]
                self.drop(list(reversed(paths)) if reverse else paths, self.window.queue_list.viewport())
                self.window.position(1500)
                self.assertEqual(self.window.canvas.subtitle, '안녕하세요')
                self.assertEqual(self.window.queue, [str(self.video)])

    def test_multiple_video_pairs_and_external_enqueue(self):
        w = self.window
        w.add_files([str(self.video)])
        second = self.root/'둘째.mp4'
        second.touch()
        sub = self.subtitle('둘째.srt', '두 번째 자막')
        w.receive_files([str(second), str(sub)])
        self.assertEqual(w.current, str(self.video))
        self.assertEqual(w.subtitles, [])
        w.next_file(1)
        w.position(1500)
        self.assertEqual(w.canvas.subtitle, '두 번째 자막')
        self.assertEqual(w.queue, [str(self.video), str(second)])

    def test_no_video_or_youtube_does_not_queue_subtitle(self):
        sub = self.subtitle()
        self.drop([sub])
        self.assertEqual(self.window.queue, [])
        self.assertIsNone(self.window.current)
        self.window.current = 'https://www.youtube.com/watch?v=M7lc1UVf-VE'
        self.window.source_kind = 'youtube'
        self.drop([sub])
        self.assertEqual(self.window.subtitles, [])
        self.assertIn('먼저', self.window.status.text())

    def test_invalid_subtitle_preserves_existing_cues(self):
        w = self.window
        w.add_files([str(self.video)])
        w.apply_subtitle(self.subtitle())
        before = w.subtitles
        bad = self.root/'깨진.smi'
        bad.write_text('<SAMI>invalid</SAMI>')
        self.drop([bad])
        self.assertEqual(w.subtitles, before)
        self.assertIn('불러오지 못했습니다', w.status.text())

    def test_uppercase_sidecar_and_utf16(self):
        self.subtitle('수업 영상.SRT', encoding='utf-16')
        self.window.add_files([str(self.video)])
        self.window.position(1500)
        self.assertEqual(self.window.canvas.subtitle, '안녕하세요')

    def test_vtt_and_cp949_sami(self):
        vtt = self.root/'test.vtt'
        vtt.write_text('WEBVTT\n\n00:01.000 --> 00:02.500 align:center\n첫째<br>둘째\n', encoding='utf-8')
        self.assertEqual(read_subtitles(vtt), [(1000, 2500, '첫째\n둘째')])
        sami = self.root/'test.sami'
        sami.write_text('<SAMI><SYNC Start=1000><P>한글<SYNC Start=2500><P>&nbsp;</SAMI>', encoding='cp949')
        self.assertEqual(read_subtitles(sami)[0], (1000, 2500, '한글'))
