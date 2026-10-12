from .controls import ActionButton
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QObject, QRunnable, Signal, QThreadPool, Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from .media_tools import ffmpeg, resource, run_ffmpeg


class Events(QObject):
    progress = Signal(str)
    finished = Signal(str, str)


class ClipJob(QRunnable):
    def __init__(self, source, start, end, folder, youtube=False, permit=None):
        super().__init__()
        if not 0 <= start < end or end-start < .1:
            raise ValueError('끝 지점은 시작 지점보다 뒤에 있어야 합니다.')
        self.source, self.start, self.end = source, start, end
        self.folder, self.youtube = Path(folder), youtube
        self.permit = permit
        self.cancel = threading.Event()
        self.events = Events()

    def run(self):
        output = None
        try:
            from .auth_gate import consume_permit
            consume_permit(self.permit, 'clip')
            self.folder.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='.ssen-clip-', dir=self.folder) as temp:
                source = self.source
                start = self.start
                if self.youtube:
                    from .youtube_url import video_id
                    import yt_dlp
                    from yt_dlp.utils import download_range_func
                    identifier = video_id(source)
                    source = f'https://www.youtube.com/watch?v={identifier}'
                    def progress(data):
                        if self.cancel.is_set(): raise InterruptedError('다운로드를 취소했습니다.')
                    self.events.progress.emit('YouTube에서 선택 구간을 가져오고 있습니다…')
                    options = {'format':'bv*[height<=1080]+ba/b[height<=1080]/best',
                        'outtmpl':str(Path(temp)/'source.%(ext)s'), 'noplaylist':True,
                        'quiet':True, 'no_warnings':True, 'socket_timeout':15, 'retries':1,
                        'fragment_retries':1, 'ffmpeg_location':ffmpeg(),
                        'external_downloader_args':{'ffmpeg_i':['-rw_timeout','15000000']},
                        'js_runtimes':{'quickjs':{'path':str(resource('assets/runtime/qjs.exe'))}},
                        'download_ranges':download_range_func([], [(self.start, self.end)]),
                        'force_keyframes_at_cuts':True, 'progress_hooks':[progress],
                        'overwrites':True, 'windowsfilenames':True}
                    with yt_dlp.YoutubeDL(options) as ydl:
                        info = ydl.extract_info(source, download=True)
                    candidates = [p for p in Path(temp).glob('source.*') if p.suffix not in ('.part', '.ytdl', '.json')]
                    if not candidates: raise RuntimeError('다운로드된 구간을 찾지 못했습니다.')
                    source = str(max(candidates, key=lambda p:p.stat().st_size))
                    start = 0
                if self.cancel.is_set(): raise InterruptedError('작업을 취소했습니다.')
                self.events.progress.emit('MP4로 저장하고 있습니다…')
                output = self.folder/f'구간_{int(self.start)}-{int(self.end)}_{datetime.now():%Y%m%d_%H%M%S_%f}.mp4'
                temporary = Path(temp)/'encoded.mp4'
                run_ffmpeg(['-y', '-ss', str(start), '-i', str(source), '-t', str(self.end-self.start),
                    '-map', '0:v:0', '-map', '0:a:0?', '-sn', '-dn', '-c:v', 'libx264',
                    '-preset', 'fast', '-crf', '21', '-pix_fmt', 'yuv420p', '-c:a', 'aac',
                    '-movflags', '+faststart', str(temporary)], self.cancel)
                if self.cancel.is_set(): raise InterruptedError('작업을 취소했습니다.')
                temporary.replace(output)
            self.events.finished.emit(str(output), '')
        except Exception as error:
            message = '작업을 취소했습니다.' if self.cancel.is_set() else str(error)
            self.events.finished.emit('', message)


class ClipDialog(QDialog):
    def __init__(self, parent, source, start, end, folder, youtube=False, permit=None):
        super().__init__(parent)
        self.setWindowTitle('선택 구간 MP4 저장')
        self.setMinimumWidth(490)
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(22,22,22,22)
        layout.addWidget(QLabel(f'{start:.1f}초 → {end:.1f}초 · {end-start:.1f}초 분량'))
        layout.addWidget(QLabel('원본 영상의 선택 구간을 저장합니다. 필기까지 녹화하려면 수업 녹화를 사용하세요.'))
        self.label = QLabel('구간 저장을 준비하고 있습니다…')
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(self.label.textInteractionFlags() | Qt.TextSelectableByMouse)
        layout.addWidget(self.label)
        self.close_button = ActionButton('취소')
        self.close_button.clicked.connect(self.reject)
        layout.addWidget(self.close_button)
        self.job = ClipJob(source, start, end, folder, youtube, permit)
        self.busy = True
        self.job.events.progress.connect(self.label.setText)
        self.job.events.finished.connect(self.done_job)
        QThreadPool.globalInstance().start(self.job)

    def done_job(self, path, error):
        self.busy = False
        self.label.setText('저장 완료\n'+path if path else '저장하지 못했습니다.\n'+error)
        self.close_button.setText('닫기')
        self.close_button.setEnabled(True)

    def reject(self):
        if self.busy:
            self.job.cancel.set()
            self.label.setText('작업을 취소하고 임시 파일을 정리하고 있습니다…')
            self.close_button.setEnabled(False)
        else: super().reject()

    def closeEvent(self, event):
        if self.busy:
            self.reject()
            event.ignore()
        else: super().closeEvent(event)
