"""One player per user, with acknowledged local file-open requests."""
import hashlib
import json
import time
import uuid
from pathlib import Path

from PySide6.QtCore import QObject, QLockFile, QStandardPaths, QTimer, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket


class SingleInstance(QObject):
    files_received = Signal(list)
    MAX_REQUEST = 1024 * 1024

    def __init__(self, parent=None, directory=None):
        super().__init__(parent)
        directory = Path(directory or QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation))
        directory.mkdir(parents=True, exist_ok=True)
        identity = str(directory.resolve()).casefold().encode('utf-8')
        self.name = 'SsenPlayer-' + hashlib.sha256(identity).hexdigest()[:24]
        self.lock = QLockFile(str(directory / 'player.lock'))
        # A long-running player must never lose its lock just because it is old.
        self.lock.setStaleLockTime(0)
        self.server = QLocalServer(self)
        self.server.setSocketOptions(QLocalServer.UserAccessOption)
        self.server.newConnection.connect(self._accept)
        self.seen = set()

    def start(self, paths, timeout=15):
        """Return True for the owner, False after delivery; fail without a new UI."""
        request = json.dumps({'id': uuid.uuid4().hex, 'paths': paths}, ensure_ascii=False).encode('utf-8') + b'\n'
        if len(request) > self.MAX_REQUEST:
            raise RuntimeError('한 번에 여는 파일이 너무 많습니다. 파일을 나누어 열어 주세요.')
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.lock.tryLock(0):
                # Only the lock owner may clean up an endpoint after a crash.
                QLocalServer.removeServer(self.name)
                if not self.server.listen(self.name):
                    self.lock.unlock()
                    raise RuntimeError('파일 전달을 준비하지 못했습니다: ' + self.server.errorString())
                return True
            if self.lock.error() != QLockFile.LockFailedError:
                raise RuntimeError('쎈플레이어 실행 정보를 저장하지 못했습니다.')
            socket = QLocalSocket()
            socket.connectToServer(self.name)
            if socket.waitForConnected(200):
                socket.write(request)
                socket.flush()
                reply = bytearray()
                while time.monotonic() < deadline:
                    if socket.bytesAvailable() or socket.waitForReadyRead(200):
                        reply.extend(bytes(socket.readAll()))
                        if b'\n' in reply:
                            socket.abort()
                            if reply == b'OK\n':
                                return False
                            raise RuntimeError('기존 쎈플레이어가 파일을 받지 못했습니다.')
                    if socket.state() == QLocalSocket.UnconnectedState:
                        break
            socket.abort()
            time.sleep(0.05)
        raise RuntimeError('기존 쎈플레이어가 응답하지 않습니다. 잠시 후 파일을 다시 열어 주세요.')

    def _accept(self):
        while self.server.hasPendingConnections():
            socket = self.server.nextPendingConnection()
            buffer = bytearray()
            timer = QTimer(socket)
            timer.setSingleShot(True)
            timer.timeout.connect(socket.abort)
            timer.start(15000)
            socket.disconnected.connect(socket.deleteLater)
            socket.readyRead.connect(lambda s=socket, b=buffer, t=timer: self._read(s, b, t))
            if socket.bytesAvailable():
                self._read(socket, buffer, timer)

    def _read(self, socket, buffer, timer):
        buffer.extend(bytes(socket.readAll()))
        if len(buffer) > self.MAX_REQUEST:
            socket.abort()
            return
        if b'\n' not in buffer:
            return
        timer.stop()
        try:
            request = json.loads(buffer)
            identifier, paths = request['id'], request['paths']
            if not isinstance(identifier, str) or len(identifier) != 32:
                raise ValueError('Invalid request ID')
            if not isinstance(paths, list) or not all(isinstance(p, str) and Path(p).is_absolute() for p in paths):
                raise ValueError('Invalid paths')
        except (ValueError, KeyError, TypeError):
            socket.abort()
            return
        if identifier not in self.seen:
            self.seen.add(identifier)
            self.files_received.emit(paths)
        socket.write(b'OK\n')
        socket.flush()
        socket.disconnectFromServer()

    def close(self):
        self.server.close()
        self.lock.unlock()
