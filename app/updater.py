"""GitHub Releases update check, like the other Ssen apps; no GitHub credentials shipped."""
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urlparse
from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QApplication
from . import VERSION


def version_tuple(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d+\.\d+\.\d+', value):
        raise ValueError('올바르지 않은 버전입니다.')
    return tuple(map(int, value.split('.')))


def https_url(value):
    parsed = urlparse(value)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('업데이트에는 HTTPS 주소만 사용할 수 있습니다.')
    return value


def canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def verify_manifest(document, feed):
    # Trust comes from HTTPS to the release itself; the installer is then checked by size and SHA-256.
    # A "signature" field, still written for 0.2.3 installs, is ignored here.
    payload = document['payload']
    version_tuple(payload['version'])
    if not https_url(payload['url']).startswith(feed.split('/releases/')[0]+'/releases/download/'):
        raise ValueError('업데이트 파일이 이 앱의 GitHub 릴리스에 있지 않습니다.')
    if not re.fullmatch('[a-f0-9]{64}', payload['sha256']):
        raise ValueError('잘못된 SHA-256입니다.')
    if type(payload['size']) is not int or not 0 < payload['size'] < 1024**3:
        raise ValueError('설치 파일 크기가 올바르지 않습니다.')
    return payload


def fetch_manifest(feed):
    with urllib.request.urlopen(https_url(feed), timeout=20) as response:
        https_url(response.url)
        data = response.read(128*1024+1)
    if len(data) > 128*1024:
        raise ValueError('업데이트 정보가 너무 큽니다.')
    return verify_manifest(json.loads(data), feed)


def download(payload):
    with tempfile.NamedTemporaryFile(prefix='SsenPlayer-Update-', suffix='.exe', delete=False) as file:
        path = Path(file.name)
        try:
            digest = hashlib.sha256()
            size = 0
            with urllib.request.urlopen(https_url(payload['url']), timeout=30) as response:
                https_url(response.url)
                while chunk := response.read(1024*1024):
                    size += len(chunk)
                    if size > payload['size']:
                        raise ValueError('설치 파일 크기가 일치하지 않습니다.')
                    digest.update(chunk)
                    file.write(chunk)
            if size != payload['size'] or digest.hexdigest() != payload['sha256']:
                raise ValueError('설치 파일 검증에 실패했습니다.')
        except Exception:
            file.close()
            path.unlink(missing_ok=True)
            raise
    return str(path)


def load_config():
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))
    try: return json.loads((base/'build/update.json').read_text('utf-8'))
    except (OSError, ValueError): return {}


def newer_release(config):
    payload = fetch_manifest(config['feed_url'])
    return payload if version_tuple(payload['version']) > version_tuple(VERSION) else None


def check_in_background(window):
    # Ask on every launch until installed; "다음에" simply waits for the next start.
    config = load_config()
    if not config.get('feed_url'): return
    window.update_task = Task(lambda: newer_release(config))
    window.update_task.signals.done.connect(window.update_checked)
    QThreadPool.globalInstance().start(window.update_task)


class Result(QObject):
    done = Signal(object, str)


class Task(QRunnable):
    def __init__(self, function):
        super().__init__()
        self.function = function
        self.signals = Result()

    def run(self):
        try: self.signals.done.emit(self.function(), '')
        except Exception as error: self.signals.done.emit(None, str(error) or type(error).__name__)


class UpdateDialog(QDialog):
    def __init__(self, parent, payload=None):
        super().__init__(parent)
        self.setWindowTitle('쎈player 업데이트')
        self.setMinimumWidth(460)
        self.busy = False
        self.payload = None
        self.installer = None
        self.config = load_config()
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.addWidget(QLabel(f'현재 버전 {VERSION}'))
        self.message = QLabel('인터넷에 연결해 새 버전을 확인합니다.')
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        self.action = QPushButton('새 버전 확인')
        self.action.clicked.connect(self.act)
        layout.addWidget(self.action)
        close = QPushButton('다음에' if payload else '닫기')
        close.clicked.connect(self.reject)
        layout.addWidget(close)
        if payload:
            self.payload = payload
            self.message.setText(f"새 버전 {payload['version']}이 나왔습니다. 지금 업데이트할까요?\n'다음에'를 누르면 다음 실행 때 다시 알려 드립니다.")
            self.action.setText('지금 업데이트')
        elif not self.config.get('feed_url'):
            self.message.setText('이 버전은 업데이트 배포 주소가 설정되지 않아 앱 안에서 업데이트할 수 없습니다.\n배포 주소를 설정한 버전부터 앱 안에서 업데이트할 수 있습니다.')
            self.action.setEnabled(False)

    def act(self):
        if self.installer:
            try:
                subprocess.Popen([self.installer, '/SILENT', '/CLOSEAPPLICATIONS', '/RESTARTAPPLICATIONS'], close_fds=True)
                QApplication.instance().closeAllWindows()
            except OSError as error:
                self.message.setText(str(error))
            return
        self.busy = True
        self.action.setEnabled(False)
        if self.payload:
            self.message.setText('업데이트를 내려받고 파일이 손상되거나 바뀌지 않았는지 확인하고 있습니다…')
            self.task = Task(lambda: download(self.payload))
            self.task.signals.done.connect(self.downloaded)
        else:
            self.message.setText('새 버전을 확인하고 있습니다…')
            self.task = Task(lambda: fetch_manifest(self.config['feed_url']))
            self.task.signals.done.connect(self.checked)
        QThreadPool.globalInstance().start(self.task)

    def checked(self, result, error):
        self.busy = False
        self.action.setEnabled(True)
        if error:
            self.message.setText('업데이트를 확인하지 못했습니다: ' + error)
        elif version_tuple(result['version']) > version_tuple(VERSION):
            self.payload = result
            self.message.setText(f"새 버전 {result['version']}을 사용할 수 있습니다.")
            self.action.setText('업데이트 다운로드')
        else:
            self.message.setText('최신 버전입니다.')

    def downloaded(self, result, error):
        self.busy = False
        self.action.setEnabled(True)
        if error:
            self.message.setText('다운로드 실패: ' + error)
        else:
            self.installer = result
            self.message.setText('서명과 파일 검증을 마쳤습니다. 앱을 종료하고 업데이트를 설치합니다.')
            self.action.setText('종료하고 설치')

    def reject(self):
        if not self.busy: super().reject()

    def closeEvent(self, event):
        if self.busy: event.ignore()
        else: super().closeEvent(event)
