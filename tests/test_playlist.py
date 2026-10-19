"""Exercise the real queue UI and source transitions without network or accounts."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PySide6.QtCore import QObject, QSettings, Signal, Qt
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtMultimedia import QMediaPlayer
from app.player import Player


class LockedAuth(QObject):
    changed = Signal(dict)
    snapshot = {'ready': True, 'canEdit': False}
    def authorize(self): return False
    def shutdown(self): pass


class FakeYouTube(QWidget):
    def __init__(self):
        super().__init__()
        self.blocker = SimpleNamespace(enabled=True)
        self.commands = []
        self.identifier = ''
        self.state = {}
    def load(self, identifier):
        self.identifier = identifier
        self.state = {}
    def command(self, *args): self.commands.append(args)
    def sync_tool(self): pass
    def shutdown(self): pass


class PlaylistTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.window = Player(QSettings(str(Path(self.temp.name)/'test.ini'), QSettings.IniFormat),
                             auth_factory=LockedAuth)
        self.window.youtube = FakeYouTube()
        self.window.video_stack.addWidget(self.window.youtube)
        self.urls, _ = self.window.add_youtube_links('M7lc1UVf-VE\naqz-KE-bpKQ')

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()
        self.temp.cleanup()

    def state(self, value=0, **extra):
        state = dict(videoId=self.window.youtube.identifier, ready=True, state=value,
                     duration=10, time=10, title='테스트 영상')
        state.update(extra)
        self.window.youtube.state = state
        self.window.youtube_state(state)
        return state

    def test_batch_add_preserves_playback_and_is_atomic(self):
        w = self.window
        self.assertIsNone(w.current)
        w.load(self.urls[0])
        with self.assertRaises(ValueError): w.add_youtube_links('dQw4w9WgXcQ\ninvalid')
        self.assertEqual(w.queue, self.urls)
        self.assertEqual(w.add_youtube_links('aqz-KE-bpKQ\ndQw4w9WgXcQ')[1], 1)
        self.assertEqual(w.current, self.urls[0])
        self.assertEqual(w.queue_list.count(), 3)

    def test_end_advances_once_and_stops_at_last_item(self):
        w = self.window
        w.load(self.urls[0])
        stale = self.state()
        self.assertEqual(w.current, self.urls[1])
        w.youtube_state(stale)
        self.assertEqual(w.current, self.urls[1])
        with patch.object(w, 'next_file', wraps=w.next_file) as next_file:
            self.state()
            self.state()
            next_file.assert_called_once_with(1, wrap=False)
        self.assertEqual(w.current, self.urls[1])
        self.assertEqual(w.queue_list.item(1).text(), 'YouTube · 테스트 영상')

    def test_repeat_segment_and_errors_do_not_advance(self):
        w = self.window
        w.load(self.urls[0])
        self.state(error=100)
        self.assertEqual(w.current, self.urls[0])
        w.loop = True
        self.state()
        self.assertIn(('seek', 0), w.youtube.commands)
        self.assertEqual(w.current, self.urls[0])
        self.state(1)
        w.a, w.b = 2000, 10000
        self.state()
        self.assertEqual(w.youtube.commands[-2:], [('seek', 2.0), ('play',)])
        self.assertEqual(w.current, self.urls[0])

    def test_reorder_delete_and_manual_navigation(self):
        w = self.window
        w.load(self.urls[0])
        w.move_queue_item(1)
        self.assertEqual(w.queue, list(reversed(self.urls)))
        w.remove_queue_item()
        self.assertEqual(len(w.queue), 2)  # Playing item remains the queue anchor.
        w.next_file(-1)
        self.assertEqual(w.current, self.urls[1])
        w.queue_list.setCurrentRow(1)
        w.remove_queue_item()
        self.assertEqual(w.queue, [self.urls[1]])

    def test_local_and_youtube_share_the_queue(self):
        w = self.window
        local = Path(self.temp.name)/'local.mp4'
        local.touch()
        with patch.object(w.media, 'play'):
            w.add_files([str(local)])
            w.next_file(1)
            self.assertEqual(w.current, self.urls[0])
            w.next_file(1)
            self.state()
            self.assertEqual(w.source_kind, 'local')
            self.assertEqual(w.current, str(local.resolve()))
            w.move_queue_item(-1)
            w.media_status(QMediaPlayer.EndOfMedia)
            self.assertEqual(w.current, self.urls[1])

    def test_old_browser_poll_is_ignored(self):
        import json
        from app.youtube import YouTubeSurface
        w = self.window
        w.load(self.urls[0])
        surface = SimpleNamespace(load_generation=2, identifier='aqz-KE-bpKQ', state={})
        YouTubeSurface.received(surface, json.dumps(dict(videoId='aqz-KE-bpKQ', state=0)), 1)
        YouTubeSurface.received(surface, json.dumps(dict(videoId='M7lc1UVf-VE', state=0)), 2)
        self.assertEqual(surface.state, {})

    def test_external_files_append_without_reloading_current_video(self):
        w = self.window
        files = [Path(self.temp.name) / name for name in ('첫 영상.mp4', '다음 영상.mp4')]
        for file in files: file.touch()
        with patch.object(w.media, 'play'):
            w.add_files([str(files[0])])
        with patch.object(w, 'load') as load:
            w.receive_files([str(files[1]), str(files[0])])
            w.receive_files([])
            load.assert_not_called()
        self.assertEqual(w.current, str(files[0].resolve()))
        self.assertEqual(w.queue, self.urls + [str(p.resolve()) for p in files])
        self.assertEqual(w.queue_list.count(), 4)

    def test_external_file_starts_in_empty_player_and_preserves_youtube(self):
        w = self.window
        local = Path(self.temp.name) / '영상.mp4'
        local.touch()
        with patch.object(w.media, 'play'):
            w.receive_files([str(local)])
        self.assertEqual(w.current, str(local.resolve()))
        w.load(self.urls[0])
        with patch.object(w, 'load') as load:
            w.receive_files([str(local)])
            load.assert_not_called()
        self.assertEqual(w.current, self.urls[0])


if __name__ == '__main__': unittest.main()
