"""GitHub Releases update check, like the other Ssen apps; no GitHub credentials shipped."""
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import threading
import html
from datetime import datetime
import urllib.request
from pathlib import Path
from urllib.parse import urlparse, quote, unquote
from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool, QSettings, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
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


def download(payload, progress=None, cancelled=None):
    with tempfile.NamedTemporaryFile(prefix='SsenPlayer-Update-', suffix='.exe', delete=False) as file:
        path = Path(file.name)
        try:
            digest = hashlib.sha256()
            size = 0
            with urllib.request.urlopen(https_url(payload['url']), timeout=30) as response:
                https_url(response.url)
                while chunk := response.read(1024*1024):
                    if cancelled and cancelled(): raise InterruptedError('다운로드를 취소했습니다.')
                    size += len(chunk)
                    if size > payload['size']:
                        raise ValueError('설치 파일 크기가 일치하지 않습니다.')
                    digest.update(chunk)
                    file.write(chunk)
                    if progress: progress(size, payload['size'])
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


def plain_notes(body):
    text = str(body or '')[:24000]
    text = re.sub(r'<[^>]*>', '', text)
    text = html.unescape(text)
    text = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'[\x00-\x08\x0b-\x1f\x7f]', '', text)
    return text.replace('**', '').replace('`', '').strip()[:6000]


def highlights(notes):
    lines = [re.sub(r'^\s*[-*•]\s+', '', line).strip() for line in notes.splitlines()
             if re.match(r'^\s*[-*•]\s+', line)]
    lines = [line for line in lines if not re.search(r'\.(exe|zip|json)\b', line, re.I)]
    return [line[:180] for line in lines[:3]] or [notes[:220] or '릴리스 설명이 없습니다. 공식 배포 페이지에서 확인해 주세요.']


def fetch_release(config):
    """Join the existing verified manifest to the same stable GitHub release."""
    payload = dict(fetch_manifest(config['feed_url']))
    repo = config['feed_url'].split('/releases/')[0]
    parsed = urlparse(repo)
    if parsed.netloc != 'github.com' or not re.fullmatch(r'/[\w.-]+/[\w.-]+', parsed.path):
        raise ValueError('공식 GitHub 배포 주소가 올바르지 않습니다.')
    tag = unquote(urlparse(payload['url']).path.split('/releases/download/')[1].split('/')[0])
    api = 'https://api.github.com/repos' + parsed.path + '/releases/tags/' + quote(tag, safe='')
    with urllib.request.urlopen(api, timeout=20) as response:
        https_url(response.url)
        raw = response.read(1024*1024+1)
    if len(raw) > 1024*1024: raise ValueError('릴리스 정보가 너무 큽니다.')
    release = json.loads(raw)
    if release.get('draft') is not False or release.get('prerelease') is not False:
        raise ValueError('정식 안정 버전이 아닙니다.')
    if release.get('tag_name') != tag or tag.removeprefix('v') != payload['version']:
        raise ValueError('릴리스 버전이 일치하지 않습니다.')
    assets = release.get('assets', [])
    installer = next((a for a in assets if a.get('browser_download_url') == payload['url']), None)
    if not installer or installer.get('size') != payload['size']:
        raise ValueError('릴리스 설치 파일 정보가 일치하지 않습니다.')
    page = repo + '/releases/tag/' + quote(tag, safe='')
    zip_asset = next((a for a in assets if a.get('name') == f"SsenPlayer-{payload['version']}-win-x64.zip"), {})
    zip_size = zip_asset.get('size')
    payload.update(notes=plain_notes(release.get('body')), page=page,
                   zip_size=zip_size if type(zip_size) is int and zip_size > 0 else None)
    return payload


def installation_mode():
    if not getattr(sys, 'frozen', False): return 'development'
    if sys.platform == 'win32':
        import winreg
        key = r'Software\Microsoft\Windows\CurrentVersion\Uninstall\{1459D467-38B3-4749-8E5B-30F20D09F772}_is1'
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as handle:
                directory = Path(winreg.QueryValueEx(handle, 'InstallLocation')[0]).resolve()
            if directory == Path(sys.executable).resolve().parent and (directory/'unins000.exe').is_file():
                return 'installed'
        except OSError:
            pass
    return 'portable'


def verify_download(path, payload):
    path = Path(path)
    if path.stat().st_size != payload['size']:
        raise ValueError('설치 파일 크기가 바뀌었습니다. 다시 다운로드해 주세요.')
    digest = hashlib.sha256()
    with path.open('rb') as file:
        while chunk := file.read(1024*1024): digest.update(chunk)
    if digest.hexdigest() != payload['sha256']:
        raise ValueError('설치 파일 검증에 실패했습니다. 다시 다운로드해 주세요.')


def launch_installer(path):
    # This guard is independent of the UI/controller, including test-injected mode.
    if installation_mode() != 'installed':
        raise RuntimeError('설치형으로 실행한 앱에서만 업데이트를 설치할 수 있습니다.')
    subprocess.Popen([str(path), '/SILENT', '/NORESTART', '/CLOSEAPPLICATIONS',
                      '/NOFORCECLOSEAPPLICATIONS', '/NORESTARTAPPLICATIONS', '/RESTARTPLAYER=1',
                      '/DIR=' + str(Path(sys.executable).resolve().parent)], close_fds=True)


class UpdatePreferences:
    """Only update preferences are writable without a license; media settings stay protected."""
    def __init__(self, settings): self.settings = settings

    def read(self, key, default=None):
        return self.settings.value('updates/' + key, default)

    def write(self, key, value):
        key = 'updates/' + key
        existed, old = self.settings.contains(key), self.settings.value(key)
        try:
            self.settings.setValue(key, value)
            self.settings.sync()
            if self.settings.status() != QSettings.NoError:
                raise OSError('사용자 설정 저장 위치에 쓸 수 없습니다.')
        except Exception as error:
            if existed: self.settings.setValue(key, old)
            else: self.settings.remove(key)
            raise OSError('업데이트 설정을 저장하지 못했습니다.') from error


class Result(QObject):
    done = Signal(object, str)
    progress = Signal(int, int)


class Task(QRunnable):
    def __init__(self, function):
        super().__init__()
        self.function, self.signals = function, Result()

    def run(self):
        try: self.signals.done.emit(self.function(self.signals.progress.emit), '')
        except Exception as error: self.signals.done.emit(None, str(error) or type(error).__name__)


class UpdateController(QObject):
    changed = Signal()
    FIRST_CHECK_MS = 15000
    RECHECK_MS = 4 * 60 * 60 * 1000

    def __init__(self, parent=None, *, settings=None, mode=None, fetcher=None, downloader=None,
                 runner=None, busy_reason=None, opener=None, installer=None, quit_app=None):
        super().__init__(parent)
        self.preferences = UpdatePreferences(settings if settings is not None else QSettings('HooniKim', 'SsenPlayer'))
        self.mode = mode or installation_mode()
        self.fetcher = fetcher or (lambda: fetch_release(load_config()))
        self.downloader = downloader or download
        self.runner = runner or self._submit
        self.busy_reason = busy_reason or (lambda: '')
        self.opener = opener or (lambda url: QDesktopServices.openUrl(QUrl(url)))
        self.installer_launcher = installer or launch_installer
        self.quit_app = quit_app or (lambda: __import__('PySide6.QtWidgets', fromlist=['QApplication']).QApplication.instance().closeAllWindows())
        self.auto_check = str(self.preferences.read('auto_check', True)).lower() not in ('false', '0')
        self.skipped = str(self.preferences.read('skipped_version', ''))
        self.last_checked = str(self.preferences.read('last_checked', ''))
        self.phase, self.error, self.payload, self.installer = 'idle', '', None, None
        self.progress = 0
        self.operation = None
        self.dismissed = set()
        self._started, self._closed, self._installing = False, False, False
        self._tasks = set()
        self.cancelled = threading.Event()
        self.first_timer, self.repeat_timer = QTimer(self), QTimer(self)
        self.first_timer.setSingleShot(True)
        self.first_timer.setInterval(self.FIRST_CHECK_MS)
        self.repeat_timer.setInterval(self.RECHECK_MS)
        self.first_timer.timeout.connect(self._first_check)
        self.repeat_timer.timeout.connect(self.check)

    @property
    def has_update(self):
        return bool(self.payload and version_tuple(self.payload['version']) > version_tuple(VERSION))

    @property
    def dot_visible(self):
        return self.has_update and self.payload['version'] != self.skipped

    @property
    def notice_key(self):
        return (self.payload['version'], 'ready' if self.installer else 'available') if self.has_update else None

    @property
    def show_notice(self):
        return self.dot_visible and self.notice_key not in self.dismissed

    def start(self):
        if self._started or self._closed: return
        self._started = True
        if self.auto_check: self.first_timer.start()

    def _first_check(self):
        if not self.auto_check or self._closed: return
        self.repeat_timer.start()
        self.check()

    def _save(self, key, value):
        try:
            self.preferences.write(key, value)
            return True
        except Exception:
            self.error = '설정 저장 실패: 자동 확인·건너뛰기 설정을 저장하지 못했습니다. 저장 위치와 권한을 확인해 주세요.'
            self.phase = 'error'
            self.changed.emit()
            return False

    def set_auto_check(self, value):
        if value == self.auto_check: return True
        if not self._save('auto_check', bool(value)): return False
        self.auto_check = bool(value)
        self.first_timer.stop()
        self.repeat_timer.stop()
        if self.auto_check and self._started: self.first_timer.start()
        self.error = ''
        self._resting_phase()
        self.changed.emit()
        return True

    def skip(self):
        if not self.has_update: return False
        version = self.payload['version']
        if not self._save('skipped_version', version): return False
        self.skipped, self.error = version, ''
        self._resting_phase()
        self.changed.emit()
        return True

    def dismiss(self):
        if self.notice_key: self.dismissed.add(self.notice_key)
        self.changed.emit()

    def _submit(self, work, done, progress=None):
        task = Task(work)
        self._tasks.add(task)
        def finished(result, error):
            self._tasks.discard(task)
            if not self._closed: done(result, error)
            elif isinstance(result, str) and result.startswith(tempfile.gettempdir()):
                Path(result).unlink(missing_ok=True)
        task.signals.done.connect(finished)
        if progress: task.signals.progress.connect(progress)
        QThreadPool.globalInstance().start(task)

    def _resting_phase(self):
        if self.operation:
            self.phase = self.operation
            return
        self.phase = 'ready' if self.installer else 'available' if self.has_update else 'current' if self.payload else 'idle'

    def check(self):
        if self._closed or self.operation: return
        self.operation = 'checking'
        self.phase, self.error = 'checking', ''
        self.changed.emit()
        self.runner(lambda progress: self.fetcher(), self._checked)

    def _checked(self, result, error):
        self.operation = None
        self.last_checked = datetime.now().astimezone().isoformat(timespec='seconds')
        self.phase = 'error' if error else 'idle'
        self.error = ('확인 실패: ' + str(error)[:300]) if error else ''
        if not error:
            # A cached newer release survives a stale CDN response too.
            if not self.payload or version_tuple(result['version']) >= version_tuple(self.payload['version']):
                if self.payload and result['version'] != self.payload['version']:
                    self._discard_installer()
                self.payload = result
            self._resting_phase()
        self._save('last_checked', self.last_checked)
        self.changed.emit()

    def action(self):
        if self._closed or not self.has_update or self.operation: return
        if self.mode != 'installed':
            try:
                repo = load_config()['feed_url'].split('/releases/')[0]
                page = self.payload.get('page', repo + '/releases/latest')
                if not https_url(page).startswith(repo + '/releases/'):
                    raise ValueError('공식 배포 페이지 주소가 올바르지 않습니다.')
                if not self.opener(page): raise OSError('공식 배포 페이지를 열지 못했습니다.')
            except Exception as error:
                self.fail(error)
            return
        if self.installer: return  # The UI must request explicit confirmation separately.
        self.operation = 'downloading'
        self.phase, self.error, self.progress = 'downloading', '', 0
        self.cancelled.clear()
        payload = dict(self.payload)
        self.changed.emit()
        self.runner(lambda progress: self.downloader(payload, progress, self.cancelled.is_set), self._downloaded, self._progress)

    def _progress(self, received, total):
        if self.operation != 'downloading': return
        self.progress = min(100, int(received * 100 / total)) if total else 0
        self.changed.emit()

    def _downloaded(self, path, error):
        self.operation = None
        if error:
            self.fail('다운로드 실패: ' + str(error)[:300])
        else:
            self.installer, self.phase, self.error = str(path), 'ready', ''
            self.changed.emit()

    def fail(self, error):
        self.phase, self.error = 'error', str(error)[:400]
        self.changed.emit()

    def install(self, confirmed=False):
        if not confirmed or self._closed or self.operation or self.mode != 'installed' or not self.installer or self._installing: return False
        reason = self.busy_reason()
        if reason:
            self.fail(reason)
            return False
        try:
            verify_download(self.installer, self.payload)
            self.installer_launcher(self.installer)
        except Exception as error:
            self._discard_installer()
            self.fail('설치 시작 실패: ' + str(error)[:300])
            return False
        self._installing = True
        self.quit_app()
        return True

    def _discard_installer(self):
        if self.installer:
            try: Path(self.installer).unlink(missing_ok=True)
            except OSError: pass
        self.installer = None

    def shutdown(self):
        self._closed = True
        self.first_timer.stop()
        self.repeat_timer.stop()
        self.cancelled.set()
        if not self._installing: self._discard_installer()
