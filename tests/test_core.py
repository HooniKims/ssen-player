import json
import tempfile
import unittest
import io
import hashlib
from unittest.mock import patch
from pathlib import Path
from PySide6.QtCore import QPointF
from app.ink import Ink, Stroke
from app.subtitles import read_subtitles
from app.updater import verify_manifest, version_tuple, https_url, download, newer_release


class CoreTests(unittest.TestCase):
    def test_undo_erase_and_redo(self):
        ink = Ink()
        stroke = Stroke('#ff0000', 10, points=[(10, 10), (100, 100)])
        ink.checkpoint()
        ink.strokes.append(stroke)
        self.assertTrue(stroke.hits(QPointF(50, 50)))
        self.assertFalse(stroke.hits(QPointF(180, 10)))
        ink.clear()
        self.assertFalse(ink.strokes)
        ink.undo()
        self.assertEqual(ink.strokes, [stroke])
        ink.undo()
        self.assertFalse(ink.strokes)
        ink.redo()
        self.assertEqual(ink.strokes, [stroke])

    def test_korean_srt_and_smi(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)/'sample.srt'
            p.write_text('1\n00:00:01,200 --> 00:00:03,400\n수업 <b>자막</b>\n', encoding='utf-8-sig')
            self.assertEqual(read_subtitles(p), [(1200, 3400, '수업 자막')])
            p = p.with_suffix('.smi')
            p.write_bytes('<SAMI><BODY><SYNC Start=1000><P>첫째<br>둘째<SYNC Start=2500><P>&nbsp;</BODY></SAMI>'.encode('cp949'))
            self.assertEqual(read_subtitles(p)[0], (1000, 2500, '첫째\n둘째'))

    def test_manifest_must_point_at_this_repositorys_release(self):
        feed = 'https://github.com/o/r/releases/latest/download/update.json'
        payload = dict(version='0.2.4', url='https://github.com/o/r/releases/download/v0.2.4/setup.exe', size=123, sha256='a'*64)
        self.assertEqual(verify_manifest(dict(payload=payload, signature='ignored'), feed)['version'], '0.2.4')
        for url in ('https://example.com/setup.exe', 'https://github.com/other/r/releases/download/v1/setup.exe'):
            with self.assertRaises(ValueError): verify_manifest(dict(payload=dict(payload, url=url)), feed)
        with self.assertRaises(ValueError): verify_manifest(dict(payload=dict(payload, sha256='xyz')), feed)

    def test_version_and_https(self):
        self.assertGreater(version_tuple('1.10.0'), version_tuple('1.9.9'))
        for url in ['http://example.com/file', 'file:///C:/a.exe', 'https://secret@example.com/a']:
            with self.assertRaises(ValueError): https_url(url)
        with self.assertRaises(ValueError): version_tuple('latest')

    def test_download_checks_hash_and_size(self):
        class Response(io.BytesIO):
            url = 'https://example.com/setup.exe'
        content = b'test installer bytes'
        payload = dict(url=Response.url, size=len(content), sha256=hashlib.sha256(content).hexdigest())
        with patch('urllib.request.urlopen', return_value=Response(content)):
            path = Path(download(payload))
        try: self.assertEqual(path.read_bytes(), content)
        finally: path.unlink()
        with patch('urllib.request.urlopen', return_value=Response(b'corrupted')):
            with self.assertRaises(ValueError): download(payload)

    def test_startup_check_follows_github_release_redirect(self):
        config = dict(feed_url='https://github.com/o/r/releases/latest/download/update.json')
        def feed(version):
            payload = dict(version=version, url='https://github.com/o/r/releases/download/v1/setup.exe', size=1, sha256='a'*64)
            class Response(io.BytesIO):
                url = 'https://release-assets.githubusercontent.com/update.json'
            return Response(json.dumps(dict(payload=payload)).encode())
        with patch('urllib.request.urlopen', return_value=feed('99.0.0')):
            self.assertEqual(newer_release(config)['version'], '99.0.0')
        with patch('urllib.request.urlopen', return_value=feed('0.0.1')):
            self.assertIsNone(newer_release(config))

if __name__ == '__main__': unittest.main()
