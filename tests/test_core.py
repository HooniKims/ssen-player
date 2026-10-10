import base64
import json
import tempfile
import unittest
import io
import hashlib
from unittest.mock import patch
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from cryptography.exceptions import InvalidSignature
from PySide6.QtCore import QPointF
from app.ink import Ink, Stroke
from app.subtitles import read_subtitles
from app.updater import canonical, verify_manifest, version_tuple, https_url, download, newer_release


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

    def test_signed_manifest_rejects_tampering(self):
        key = Ed25519PrivateKey.generate()
        public = base64.b64encode(key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).decode()
        payload = dict(version='0.2.0', url='https://example.com/setup.exe', size=123, sha256='a'*64)
        doc = dict(payload=payload, signature=base64.b64encode(key.sign(canonical(payload))).decode())
        self.assertEqual(verify_manifest(doc, public)['version'], '0.2.0')
        doc['payload']['url'] = 'https://example.com/other.exe'
        with self.assertRaises(InvalidSignature): verify_manifest(doc, public)

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
        key = Ed25519PrivateKey.generate()
        public = base64.b64encode(key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).decode()
        config = dict(feed_url='https://github.com/o/r/releases/latest/download/update.json', public_key=public)
        def feed(version):
            payload = dict(version=version, url='https://github.com/o/r/releases/download/v1/setup.exe', size=1, sha256='a'*64)
            class Response(io.BytesIO):
                url = 'https://release-assets.githubusercontent.com/update.json'
            body = json.dumps(dict(payload=payload, signature=base64.b64encode(key.sign(canonical(payload))).decode()))
            return Response(body.encode())
        with patch('urllib.request.urlopen', return_value=feed('99.0.0')):
            self.assertEqual(newer_release(config)['version'], '99.0.0')
        with patch('urllib.request.urlopen', return_value=feed('0.0.1')):
            self.assertIsNone(newer_release(config))


if __name__ == '__main__': unittest.main()
