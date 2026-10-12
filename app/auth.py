"""Shared authentication in an isolated WebEngine engine, separate from the UI.

The supplied service/throttle remain byte-identical. Only this private engine can
read the store or talk to the fixed authentication server. UI state never grants
native edit permission; authorize executes the service's token verification.
"""
import json
import time
import uuid
from pathlib import Path
from PySide6.QtCore import (QObject, Signal, Slot, QTimer, QUrl, QEventLoop, QRunnable,
                            QThreadPool, QStandardPaths)
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from .auth_store import SharedStore
from .auth_network import AuthNetwork
from .media_tools import resource
from . import VERSION

ACTIONS = {'init', 'sync', 'send', 'login', 'trial', 'refresh', 'register', 'redeem',
           'eduSend', 'eduVerify', 'devices', 'deactivate', 'logout'}
CACHE_FIELDS = {'savedAt', 'verdict', 'canEdit', 'hasLicense', 'accountPresent', 'loggedIn',
                'registered', 'plan', 'expiresAt', 'unlimited', 'edu'}

class TaskEvents(QObject):
    done = Signal(str, str)

class StoreTask(QRunnable):
    def __init__(self, store, identifier, request):
        super().__init__()
        self.store, self.identifier, self.request = store, identifier, request
        self.events = TaskEvents()
    def run(self):
        result = self.store.request(self.request)
        self.events.done.emit(self.identifier, json.dumps(result, ensure_ascii=False))

class LocalPage(QWebEnginePage):
    def __init__(self, profile, entry, parent):
        super().__init__(profile, parent)
        self.entry = QUrl.fromLocalFile(str(entry.resolve()))
        self.settings().setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, False)
        self.settings().setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        self.settings().setAttribute(QWebEngineSettings.JavascriptCanOpenWindows, False)
        self.settings().setAttribute(QWebEngineSettings.JavascriptCanAccessClipboard, False)
    def acceptNavigationRequest(self, url, navigation_type, main):
        return main and url.isLocalFile() and url.toLocalFile() == self.entry.toLocalFile() and not url.hasQuery()
    def createWindow(self, kind): return None
    def javaScriptConsoleMessage(self, level, message, line, source):
        # Never echo JS errors containing input, account state or bridge payloads.
        if level == QWebEnginePage.ErrorMessageLevel:
            self.parent().setProperty('auth_script_error', True)

class EngineBridge(QObject):
    reply = Signal(str, str)
    def __init__(self, controller):
        super().__init__(controller)
        self.controller = controller
        self.jobs = {}
    @Slot(str, str)
    def rpc(self, identifier, text):
        if len(text) > 1024 * 1024 or len(identifier) > 50 or len(self.jobs) >= 8:
            self.reply.emit(identifier, '{"bridgeError":"BAD_OPERATION"}')
            return
        try:
            request = json.loads(text)
            if not isinstance(request, dict): raise ValueError()
            operation = request.get('op')
            if operation == 'api':
                self.controller.network.request(request, lambda result: self.reply.emit(identifier, json.dumps(result)))
            elif operation in ('read', 'write'):
                job = StoreTask(self.controller.store, identifier, request)
                self.jobs[identifier] = job
                job.events.done.connect(self.store_done)
                QThreadPool.globalInstance().start(job)
            else: raise ValueError()
        except Exception: self.reply.emit(identifier, '{"bridgeError":"BAD_OPERATION"}')
    @Slot(str, str)
    def store_done(self, key, result):
        self.jobs.pop(key, None)
        self.reply.emit(key, result)
    @Slot()
    def ready(self):
        self.controller.ready = True
        self.controller.engineReady.emit()
    @Slot(str)
    def state(self, text): self.controller.receive_state(text)
    @Slot(str, str)
    def complete(self, identifier, text):
        callback = self.controller.pending.pop(identifier, None)
        if callback:
            try: callback(json.loads(text))
            except (ValueError, TypeError): callback({'ok': False})
    @Slot(result=str)
    def loadCache(self):
        try: return json.dumps(self.controller.read_cache())
        except Exception: return 'null'
    @Slot(str)
    def saveCache(self, text):
        try:
            data = json.loads(text)
            # The cached educational fields are explicitly selected; no email/IDs.
            keep = {k: v for k, v in data.items() if k in CACHE_FIELDS and k != 'edu'}
            if isinstance(data.get('edu'), dict):
                keep['edu'] = {k: v for k, v in data['edu'].items() if k in ('status', 'expiresAt', 'reverifyAfter', 'eligible')}
            path = self.controller.cache_path
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix('.tmp')
            temporary.write_text(json.dumps(keep), 'utf-8')
            temporary.replace(path)
        except Exception: pass

class UIBridge(QObject):
    reply = Signal(str, str)
    changed = Signal(str)
    def __init__(self, controller, dialog):
        super().__init__(dialog)
        self.controller, self.dialog = controller, dialog
        controller.changed.connect(lambda state: self.changed.emit(json.dumps(state)))
    @Slot(result=str)
    def info(self): return json.dumps({'version': VERSION})
    @Slot(str, str, str)
    def command(self, identifier, action, text):
        if action not in ACTIONS or len(text) > 8192 or len(identifier) > 50:
            self.reply.emit(identifier, '{"ok":false,"error":"BAD_OPERATION","state":{}}')
            return
        try:
            args = json.loads(text)
            if not isinstance(args, dict): raise ValueError()
        except ValueError:
            self.reply.emit(identifier, '{"ok":false,"error":"BAD_OPERATION","state":{}}')
            return
        self.controller.authorized_until = 0
        self.controller.command(action, args, lambda result: self.reply.emit(identifier, json.dumps(result)))
    @Slot(str)
    def copyText(self, text):
        if len(text) <= 100000: QApplication.clipboard().setText(text)
    @Slot(str)
    def openExternal(self, text):
        # The supplied UI only needs the official privacy explanation.
        if text == 'https://ssenbox.lovable.app/privacy': QDesktopServices.openUrl(QUrl(text))
    @Slot()
    def close(self): self.dialog.hide()

class AuthController(QObject):
    changed = Signal(dict)
    engineReady = Signal()
    def __init__(self, parent=None, store=None, cache_path=None, network=None):
        super().__init__(parent)
        self.store = store or SharedStore()
        self.network = network or AuthNetwork(self)
        self.cache_path = Path(cache_path) if cache_path else Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation))/'auth-last.json'
        self.snapshot = {'ready': False, 'canEdit': False, 'verdict': 'LOGIN'}
        self.ready = False
        self.pending = {}
        self.authorized_until = 0
        self.authorizing = False
        self.dialog = None
        self.profile = QWebEngineProfile(self)
        self.page = LocalPage(self.profile, resource('assets/auth/engine.html'), self)
        self.channel = QWebChannel(self.page)
        self.bridge = EngineBridge(self)
        self.channel.registerObject('native', self.bridge)
        self.page.setWebChannel(self.channel)
        self.page.renderProcessTerminated.connect(self.engine_failed)
        self.page.load(self.page.entry)
        self.idle_timer = QTimer(self)
        self.idle_timer.timeout.connect(self.set_idle)
        self.idle_timer.start(15000)
    def read_cache(self):
        data = json.loads(self.cache_path.read_text('utf-8'))
        return {k: v for k, v in data.items() if k in CACHE_FIELDS}
    def set_idle(self):
        parent = self.parent()
        active = getattr(getattr(parent, 'canvas', None), 'drawing', False)
        active |= getattr(getattr(parent, 'recorder', None), 'active', False)
        # Windows idle time prevents background refresh while the teacher is writing.
        try:
            import ctypes
            class LastInput(ctypes.Structure):
                _fields_ = [('size', ctypes.c_uint), ('tick', ctypes.c_uint)]
            info = LastInput(ctypes.sizeof(LastInput), 0)
            ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info))
            idle = ((ctypes.windll.kernel32.GetTickCount() & 0xffffffff) - info.tick) & 0xffffffff
        except Exception: idle = 0
        self.page.runJavaScript('globalThis.SsenRuntime?.idle(' + ('true' if not active and idle >= 10000 else 'false') + ')')
    def engine_failed(self, *args):
        self.ready = False
        self.authorized_until = 0
        self.receive_state('{"ready":true,"canEdit":false,"verdict":"BRIDGE"}')
        callbacks, self.pending = list(self.pending.values()), {}
        for callback in callbacks: callback({'ok': False})
    def receive_state(self, text):
        try:
            state = json.loads(text)
            if not isinstance(state, dict): return
        except ValueError: return
        self.snapshot = state
        if not state.get('canEdit') or state.get('provisional'): self.authorized_until = 0
        self.changed.emit(state)
    def command(self, action, args, callback):
        if not self.ready:
            callback({'ok': False, 'error': 'BRIDGE', 'state': self.snapshot})
            return
        if action not in ACTIONS | {'authorize'}:
            callback({'ok': False, 'error': 'BAD_OPERATION', 'state': self.snapshot})
            return
        identifier = uuid.uuid4().hex
        self.pending[identifier] = callback
        self.page.runJavaScript('SsenRuntime.command(' + ','.join(json.dumps(x) for x in (identifier, action, args)) + ')')
        def timeout():
            pending = self.pending.pop(identifier, None)
            if pending: pending({'ok': False, 'error': 'BRIDGE_TIMEOUT', 'state': self.snapshot})
        QTimer.singleShot(30000, self, timeout)
    def can_edit(self):
        return self.ready and time.monotonic() < self.authorized_until
    def authorize(self):
        if self.can_edit(): return True
        if not self.ready or self.authorizing: return False
        self.authorizing = True
        result = {}
        loop = QEventLoop()
        def done(value):
            result.update(value)
            loop.quit()
        try:
            self.command('authorize', {}, done)
            if not result: loop.exec()
            valid = result.get('ok') is True and result.get('state', {}).get('canEdit') is True
            if valid:
                expiry = result['state'].get('expiresAt')
                ttl = min(60, max(0, expiry - time.time())) if isinstance(expiry, (int, float)) and expiry > 0 else 60
                self.authorized_until = time.monotonic() + ttl
            return valid
        finally: self.authorizing = False
    def show(self):
        if self.dialog is None:
            self.dialog = QDialog(self.parent())
            self.dialog.setWindowTitle('쎈Player 이용권')
            self.dialog.resize(760, 720)
            layout = QVBoxLayout(self.dialog)
            layout.setContentsMargins(0, 0, 0, 0)
            self.view = QWebEngineView(self.dialog)
            page = LocalPage(self.profile, resource('assets/auth/ui.html'), self)
            channel = QWebChannel(page)
            bridge = UIBridge(self, self.dialog)
            channel.registerObject('native', bridge)
            page.setWebChannel(channel)
            self.view.setPage(page)
            self.ui_page, self.ui_channel, self.ui_bridge = page, channel, bridge
            layout.addWidget(self.view)
            page.load(page.entry)
        else:
            self.ui_page.runJavaScript('window.SsenAuthUI?.open()')
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()

    def shutdown(self):
        # Delete pages before their off-the-record profile to stop Chromium cleanly.
        import shiboken6
        self.idle_timer.stop()
        self.ready = False
        self.authorized_until = 0
        for name in ('ui_page', 'page'):
            page = getattr(self, name, None)
            if page is not None and shiboken6.isValid(page): shiboken6.delete(page)
        if shiboken6.isValid(self.profile): shiboken6.delete(self.profile)
