"""Lazy-loaded YouTube embed and Brave adblock-rust request filtering."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from PySide6.QtCore import Qt, QUrl, QTimer, Signal, QPointF, QEvent
from PySide6.QtGui import QPainter, QImage, QColor
from PySide6.QtWidgets import QWidget
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage, QWebEngineSettings, QWebEngineUrlRequestInterceptor, QWebEngineScript
from .media_tools import resource
from .youtube_url import video_id


class AdBlock(QWebEngineUrlRequestInterceptor):
    def __init__(self, parent=None):
        super().__init__(parent)
        import adblock
        filters = adblock.FilterSet()
        filters.add_filters(resource('assets/web/adblock.txt').read_text('utf-8').splitlines())
        self.engine = adblock.Engine(filters)
        self.enabled = True
        self.blocked = 0

    def interceptRequest(self, info):
        if not self.enabled: return
        url = info.requestUrl().toString()
        source = info.firstPartyUrl().toString()
        if not url.startswith('https://'): return
        kind = info.resourceType().name.lower()
        resource_type = ('script' if 'script' in kind else 'image' if 'image' in kind else
                         'media' if 'media' in kind else 'subdocument' if 'subframe' in kind else
                         'xmlhttprequest' if 'xhr' in kind else 'other')
        try:
            if self.engine.check_network_urls(url, source, resource_type).matched:
                self.blocked += 1
                info.block(True)
        except Exception:
            pass  # A malformed rule must not break video playback.


class EmbedServer:
    def __init__(self):
        document = resource('assets/web/player.html').read_bytes()
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if urlparse(self.path).path not in ('/', '/player.html'):
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
                self.send_header('Content-Length', str(len(document)))
                self.end_headers()
                self.wfile.write(document)
            def log_message(self, *args): pass
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.origin = f'http://127.0.0.1:{self.server.server_port}'

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class InkOverlay(QWidget):
    def __init__(self, model, parent):
        super().__init__(parent)
        self.model = model
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_AcceptTouchEvents)

    def point(self, p):
        return QPointF(p.x()*1920/max(1, self.width()), p.y()*1080/max(1, self.height()))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.scale(self.width()/1920, self.height()/1080)
        self.model.ink.paint(p)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.model.begin(self.point(event.position()))
            self.update()
            event.accept()

    def mouseMoveEvent(self, event):
        self.model.move(self.point(event.position()))
        self.update()

    def mouseReleaseEvent(self, event):
        self.model.move(self.point(event.position()))
        self.model.drawing = False
        self.update()

    def event(self, event):
        kind = event.type()
        if kind in (QEvent.TouchBegin, QEvent.TouchUpdate, QEvent.TouchEnd, QEvent.TouchCancel):
            points = event.points()
            if points:
                point = self.point(points[0].position())
                if kind == QEvent.TouchBegin: self.model.begin(point)
                else: self.model.move(point)
            if kind in (QEvent.TouchEnd, QEvent.TouchCancel): self.model.drawing = False
            self.update()
            event.accept()
            return True
        if kind in (QEvent.TabletPress, QEvent.TabletMove, QEvent.TabletRelease):
            if kind == QEvent.TabletPress: self.model.begin(self.point(event.position()))
            else: self.model.move(self.point(event.position()))
            if kind == QEvent.TabletRelease: self.model.drawing = False
            self.update()
            event.accept()
            return True
        return super().event(event)


class YouTubeSurface(QWidget):
    stateChanged = Signal(dict)
    message = Signal(str)

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        self.server = EmbedServer()
        self.view = QWebEngineView(self)
        self.profile = QWebEngineProfile(self)
        self.profile.setHttpCacheType(QWebEngineProfile.MemoryHttpCache)
        self.blocker = AdBlock(self.profile)
        self.profile.setUrlRequestInterceptor(self.blocker)
        self.page = QWebEnginePage(self.profile, self.view)
        self.view.setPage(self.page)
        self.page.settings().setAttribute(QWebEngineSettings.PlaybackRequiresUserGesture, False)
        self.page.settings().setAttribute(QWebEngineSettings.FullScreenSupportEnabled, False)
        self.page.settings().setAttribute(QWebEngineSettings.JavascriptCanOpenWindows, False)
        script = QWebEngineScript()
        script.setName('SsenPlayer available-ad-skip')
        script.setInjectionPoint(QWebEngineScript.DocumentReady)
        script.setWorldId(QWebEngineScript.MainWorld)
        script.setRunsOnSubFrames(True)
        script.setSourceCode("setInterval(()=>{if(!window.__ssenDisableSkip)document.querySelectorAll('.ytp-ad-skip-button,.ytp-skip-ad-button,.ytp-ad-skip-button-modern').forEach(b=>{if(b.offsetWidth)b.click()})},500)")
        self.page.scripts().insert(script)
        self.overlay = InkOverlay(model, self)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(250)
        self.state = {}
        self.identifier = ''
        self.last_error = None
        self.sync_tool()

    def load(self, identifier):
        self.identifier = video_id(identifier)
        self.state = {}
        self.last_error = None
        self.view.setUrl(QUrl(f'{self.server.origin}/player.html?v={self.identifier}'))
        self.timer.start()

    def poll(self):
        if not self.isVisible(): return
        self.page.runJavaScript('JSON.stringify(window.ssenState || {})', self.received)

    def received(self, data):
        try: state = json.loads(data or '{}')
        except (ValueError, TypeError): return
        self.state = state
        self.stateChanged.emit(state)
        error = state.get('error')
        if error and error != self.last_error:
            self.last_error = error
            messages = {100:'삭제되었거나 비공개인 영상입니다.', 101:'이 영상은 외부 임베드 재생이 허용되지 않습니다.',
                        150:'이 영상은 외부 임베드 재생이 허용되지 않습니다.', 153:'YouTube가 임베드 앱 식별을 거부했습니다.'}
            self.message.emit(messages.get(error, f'YouTube 재생 오류: {error}')+' 차단을 끄고 재시도할 수 있습니다.')

    def command(self, name, *args):
        self.page.runJavaScript('window.ssenCommand && window.ssenCommand('+json.dumps(name)+','+json.dumps(args)+')')

    def set_blocking(self, enabled):
        self.blocker.enabled = enabled
        # Disable injected skip behavior as well as request filtering.
        scripts = self.page.scripts()
        for script in scripts.toList():
            if script.name() == 'SsenPlayer available-ad-skip':
                scripts.remove(script)
                if enabled: scripts.insert(script)
        if enabled and not any(s.name() == 'SsenPlayer available-ad-skip' for s in scripts.toList()):
            script = QWebEngineScript()
            script.setName('SsenPlayer available-ad-skip')
            script.setInjectionPoint(QWebEngineScript.DocumentReady)
            script.setWorldId(QWebEngineScript.MainWorld)
            script.setRunsOnSubFrames(True)
            script.setSourceCode("setInterval(()=>document.querySelectorAll('.ytp-ad-skip-button,.ytp-skip-ad-button,.ytp-ad-skip-button-modern').forEach(b=>{if(b.offsetWidth)b.click()}),500)")
            scripts.insert(script)
        self.view.reload()

    def sync_tool(self):
        self.overlay.setAttribute(Qt.WA_TransparentForMouseEvents, self.model.tool == 'pointer')
        self.overlay.setCursor(Qt.ArrowCursor if self.model.tool == 'pointer' else Qt.CrossCursor)
        self.overlay.update()

    def resizeEvent(self, event):
        width = min(self.width(), int(self.height()*16/9))
        height = int(width*9/16)
        x, y = (self.width()-width)//2, (self.height()-height)//2
        self.view.setGeometry(x, y, width, height)
        self.overlay.setGeometry(x, y, width, height)
        self.overlay.raise_()

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor('#111d19'))

    def capture(self):
        if not self.state.get('ready') or self.state.get('error'):
            raise ValueError('YouTube 영상이 준비된 뒤 캡처해 주세요.')
        # grab only the embed surface; desktop notifications and toolbar are excluded.
        frame = self.view.grab().toImage()
        result = frame.scaled(1920, 1080, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        p = QPainter(result)
        p.setRenderHint(QPainter.Antialiasing)
        self.model.ink.paint(p)
        p.end()
        return result

    def shutdown(self):
        self.timer.stop()
        self.command('pause')
        self.view.setUrl(QUrl('about:blank'))
        self.server.close()
