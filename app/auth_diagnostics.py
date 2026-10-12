"""Isolated packaged QA: fake server issues no valid license, never touches shared accounts."""
import json
import tempfile
import time
from pathlib import Path
from PySide6.QtCore import QObject, QTimer, QSettings, QPointF
from PySide6.QtTest import QTest
from PySide6.QtGui import QImage
from .auth import AuthController
from .auth_store import SharedStore
from .auth_network import validate_request

class FakeServer(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.calls = []
    def request(self, request, done):
        path, method, headers, raw = validate_request(request)
        body = json.loads(raw) if raw else None
        self.calls.append((path, body))
        payload = {'/auth/otp/verify': {'accountToken':'a'*43,'accountId':'test-account','expiresAt':int(time.time())+86400},
            '/status': {'edu':None,'devices':[]}, '/challenge':{'nonce':'diagnostic-nonce'},
            '/devices/register':{'regId':'test-registration'}, '/keys':{'keyList':None},
            '/license/token':{'token':'invalid.invalid.invalid'}}.get(path, {})
        # Deliberately unsigned: even this test route can never unlock editing.
        QTimer.singleShot(0, self, lambda:done({'status':200,'body':json.dumps(payload),'spec':'5.0.0','serverTime':int(time.time())}))

def create_window(output):
    from .player import Player
    temporary = tempfile.TemporaryDirectory(prefix='ssen-auth-qa-')
    root = Path(temporary.name)
    def factory(parent):
        return AuthController(parent, SharedStore(root/'v4.bin', r'Local\SsenPlayerIsolatedQA'), root/'cache.json', FakeServer(parent))
    settings = QSettings(str(root/'settings.ini'), QSettings.IniFormat)
    window = Player(settings, auth_factory=factory)
    window._qa_temporary = temporary
    window.capture_dir = str(root/'exports')
    window._qa_root = root
    return window

def run(application, window, output):
    output = Path(output)
    output.mkdir(parents=True,exist_ok=True)
    report = {}
    def wait(condition, seconds=20):
        deadline=time.monotonic()+seconds
        while not condition():
            if time.monotonic()>deadline: raise AssertionError('Diagnostic timed out')
            QTest.qWait(30)
    def command(action, args=None):
        result=[]
        window.auth.command(action,args or {},result.append)
        wait(lambda:bool(result))
        return result[0]
    def check():
        try:
            auth=window.auth
            wait(lambda:auth.ready and auth.snapshot.get('ready'))
            assert not auth.authorize()
            report['anonymous_denied']=True
            if window.current:
                wait(lambda:window.canvas.video.videoSink().videoFrame().isValid())
                report['read_only_playback']=True
                window.media.pause()
            auth.snapshot['canEdit']=True  # A renderer/display value never grants native permission.
            assert not auth.authorize()
            report['display_state_cannot_unlock']=True
            window.capture()
            wait(lambda:auth.dialog is not None)
            QTest.qWait(1000)
            assert not window.jobs and not Path(window.capture_dir).exists()
            window.canvas.set_tool('pen')
            window.canvas.stroke_begin(QPointF(500,400))
            assert not window.canvas.ink.strokes
            window.undo(); window.redo(); window.clear_ink()
            report['ui_and_direct_ink_denied']=True
            from .player import SaveCapture
            from .clips import ClipJob
            capture=SaveCapture(QImage(10,10,QImage.Format_RGB32),Path(window.capture_dir)/'blocked.png')
            failed=[]
            capture.signals.done.connect(lambda path,error:failed.append((path,error)))
            capture.run()
            clip=ClipJob('missing.mov',0,1,window.capture_dir)
            clip.events.finished.connect(lambda path,error:failed.append((path,error)))
            clip.run()
            assert len(failed)==2 and all(not path and error for path,error in failed)
            try: window.recorder.start(window.capture_dir,False,False)
            except PermissionError: pass
            else: raise AssertionError('Recording was not blocked')
            window.settings.setValue('blocked','must-not-persist'); window.settings.sync()
            assert window.settings.value('blocked') is None
            assert not Path(window.capture_dir).exists()
            report['native_capture_clip_record_settings_denied']=True
            QTest.qWait(500)
            window.grab().save(str(output/'protected-player.png'))
            auth.dialog.grab().save(str(output/'license-window.png'))
            assert not auth.property('auth_script_error')
            report['auth_ui_no_script_errors']=True
            prompt, setup=window.default_app_dialog()
            assert prompt.windowTitle()=='기본 동영상 앱 설정'
            assert setup.text()=='기본 앱 설정 열기'
            assert {b.text() for b in prompt.buttons()}=={'기본 앱 설정 열기','나중에'}
            assert all('??' not in text and '\ufffd' not in text for text in
                       [prompt.text(),prompt.informativeText(),*[b.text() for b in prompt.buttons()]])
            prompt.show(); QTest.qWait(200)
            prompt.grab().save(str(output/'default-app-korean.png'))
            prompt.reject()
            report['default_app_korean_labels']=True
            window.set_mode('pure'); QTest.qWait(100)
            assert not window.auth_notice.isVisible()
            window.set_mode('window')
            assert window.auth_notice.isVisible()
            report['pure_fullscreen_hides_auth_banner']=True
            result=command('login',{'email':'teacher@senedu.kr','code':'123456'})
            registration=next(body for path,body in auth.network.calls if path=='/devices/register')
            assert registration['app']=='ssen-player'
            assert not auth.authorize()  # Fake server's unsigned response is never accepted.
            report['real_browser_engine_app_scope_and_signature_rejection']=True
            cache=auth.cache_path.read_text('utf-8') if auth.cache_path.exists() else '{}'
            assert 'teacher@' not in cache and 'accountToken' not in cache and 'test-account' not in cache
            report['cache_excludes_account_data']=True
            assert auth.ui_channel.registeredObjects().keys()=={'native'}
            assert not hasattr(auth.ui_bridge,'rpc')
            report['ui_has_no_store_or_network_bridge']=True
            print(json.dumps(report),flush=True)
            (output/'report.json').write_text(json.dumps(report,indent=2),'utf-8')
            application.exit(0)
        except Exception as error:
            # No exception payloads: test failures must not leak auth data.
            report['failure']=type(error).__name__
            (output/'report.json').write_text(json.dumps(report,indent=2),'utf-8')
            print('Auth diagnostic failed:',type(error).__name__,flush=True)
            application.exit(1)
    QTimer.singleShot(500,check)
