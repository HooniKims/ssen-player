import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


class SingleInstanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.children = []

    def tearDown(self):
        (self.root/'stop').touch()
        for child in self.children:
            try: child.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.communicate()
        self.temp.cleanup()

    def launch(self, mode='normal', *paths):
        child = subprocess.Popen([sys.executable, str(Path(__file__).with_name('instance_process.py')),
                                  str(self.root), mode, *paths], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.children.append(child)
        return child

    def wait_owner(self):
        deadline = time.monotonic() + 5
        while not (self.root/'owner').exists():
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.025)

    def test_startup_delivery_unicode_multiple_files_and_empty_launch(self):
        owner = self.launch('delayed')
        self.wait_owner()
        paths = [str(self.root/'한글 공백 영상.mp4'), str(self.root/'두 번째.mov')]
        for batch in (paths, []):
            child = self.launch('normal', *batch)
            out, err = child.communicate(timeout=6)
            self.assertEqual(child.returncode, 0, err.decode())
            self.assertEqual(out.strip(), b'forwarded')
        rows = [json.loads(row) for row in (self.root/'received.jsonl').read_text('utf-8').splitlines()]
        self.assertEqual(rows, [paths, []])
        self.assertIsNone(owner.poll())

    def test_simultaneous_launches_have_exactly_one_owner(self):
        children = [self.launch('normal', str(self.root/f'{i}.mp4')) for i in range(6)]
        self.wait_owner()
        deadline = time.monotonic() + 8
        while sum(p.poll() is not None for p in children) != 5:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.025)
        self.assertEqual(sum(p.poll() is None for p in children), 1)
        rows = (self.root/'received.jsonl').read_text('utf-8').splitlines()
        self.assertEqual(len(rows), 5)
        self.assertEqual(len({json.loads(row)[0] for row in rows}), 5)

    def test_crashed_owner_can_be_replaced(self):
        import psutil
        owner = self.launch()
        self.wait_owner()
        original_pid = int((self.root/'owner').read_text())
        # Windows venv python.exe can be a launcher with a separate interpreter PID.
        psutil.Process(original_pid).kill()
        owner.communicate()
        (self.root/'owner').unlink()
        replacement = self.launch()
        self.wait_owner()
        self.assertIsNone(replacement.poll())
        self.assertNotEqual(int((self.root/'owner').read_text()), original_pid)

    def test_partial_request_and_retry_are_delivered_once(self):
        from PySide6.QtCore import QCoreApplication
        from PySide6.QtNetwork import QLocalSocket
        from app.single_instance import SingleInstance
        app = QCoreApplication.instance() or QCoreApplication([])
        self.launch()
        self.wait_owner()
        probe = SingleInstance(directory=self.root)
        paths = [str(self.root/'긴 한글 경로.mp4')]
        request = json.dumps({'id': 'a' * 32, 'paths': paths}).encode() + b'\n'
        for attempt in range(2):
            socket = QLocalSocket()
            socket.connectToServer(probe.name)
            self.assertTrue(socket.waitForConnected(1000))
            socket.write(request[:10])
            socket.flush()
            self.assertFalse(socket.waitForReadyRead(50))
            socket.write(request[10:])
            socket.flush()
            self.assertTrue(socket.waitForReadyRead(1000))
            self.assertEqual(bytes(socket.readAll()), b'OK\n')
            socket.abort()
        rows = (self.root/'received.jsonl').read_text('utf-8').splitlines()
        self.assertEqual([json.loads(row) for row in rows], [paths])
