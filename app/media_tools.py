"""Bundled media tooling. Executables are launched without a console or shell."""
import subprocess
import sys
from pathlib import Path


def resource(relative):
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent)) / relative


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def process_options():
    return {'creationflags': subprocess.CREATE_NO_WINDOW} if sys.platform == 'win32' else {}


def run_ffmpeg(args, cancel=None):
    """Cancellable encoder; log goes to a temporary file to avoid pipe deadlocks."""
    import tempfile
    with tempfile.TemporaryFile() as log:
        child = subprocess.Popen([ffmpeg(), '-hide_banner', '-loglevel', 'error', '-nostdin', *args],
                                 stdout=subprocess.DEVNULL, stderr=log, **process_options())
        try:
            while True:
                try:
                    code = child.wait(timeout=.2)
                    break
                except subprocess.TimeoutExpired:
                    if cancel and cancel.is_set():
                        child.terminate()
                        child.wait(timeout=10)
                        raise InterruptedError('작업을 취소했습니다.')
            if code:
                log.seek(0)
                raise RuntimeError(log.read().decode('utf-8', 'replace')[-2000:] or '영상 처리에 실패했습니다.')
        finally:
            if child.poll() is None:
                child.kill()
                child.wait()
