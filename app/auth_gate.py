"""Native edit boundary. One-use permits authorize queued exports before any writes."""
import secrets
import threading
import time
from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication

_lock = threading.Lock()
_permits = {}

def authorized():
    app = QApplication.instance()
    if app is None or QThread.currentThread() != app.thread(): return False
    controller = getattr(app, 'auth_controller', None)
    return controller is not None and controller.authorize()

def require_authorized():
    if not authorized(): raise PermissionError('이용권 인증 후 사용할 수 있습니다.')

def issue_permit(operation):
    require_authorized()
    token = secrets.token_hex(32)
    with _lock:
        now = time.monotonic()
        for old in list(_permits):
            if _permits[old][1] < now: _permits.pop(old)
        _permits[token] = (operation, now + 30)
    return token

def consume_permit(token, operation):
    with _lock: grant = _permits.pop(token, None)
    if not grant or grant[0] != operation or grant[1] < time.monotonic():
        raise PermissionError('이용권을 확인한 뒤 다시 저장해 주세요.')

def revoke_permits():
    with _lock: _permits.clear()

class ProtectedSettings:
    """Read remains available; automatic playback persistence is skipped when locked."""
    def __init__(self, settings): self._settings = settings
    def value(self, *args, **kwargs): return self._settings.value(*args, **kwargs)
    def setValue(self, key, value):
        if authorized(): self._settings.setValue(key, value)
    def sync(self): self._settings.sync()
