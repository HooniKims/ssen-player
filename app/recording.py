"""Bounded-memory, real-time composite recording with optional WASAPI/mic audio."""
import queue
import threading
import time
import wave
import subprocess
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QTimer, Qt, QSize
from PySide6.QtGui import QImage
from .media_tools import ffmpeg, process_options, run_ffmpeg


class AudioTrack:
    def __init__(self, device, path, pa):
        import pyaudiowpatch as p
        self.rate = int(device['defaultSampleRate'])
        self.channels = min(2, int(device['maxInputChannels']))
        if self.channels < 1:
            raise RuntimeError('선택한 오디오 장치의 소리를 녹음할 수 없습니다.')
        self.path = path
        self.error = None
        self.file = wave.open(str(path), 'wb')
        self.file.setnchannels(self.channels)
        self.file.setsampwidth(2)
        self.file.setframerate(self.rate)
        def callback(data, count, info, status):
            try:
                self.file.writeframesraw(data)
                return None, p.paContinue
            except Exception as error:
                self.error = str(error)
                return None, p.paAbort
        try:
            self.stream = pa.open(format=p.paInt16, channels=self.channels, rate=self.rate,
                                  input=True, input_device_index=device['index'],
                                  frames_per_buffer=1024, stream_callback=callback, start=False)
        except Exception:
            self.file.close()
            raise

    def start(self): self.stream.start_stream()

    def stop(self):
        if self.stream.is_active(): self.stream.stop_stream()
        self.stream.close()
        self.file.close()
        if self.error: raise RuntimeError(self.error)


class Recorder(QObject):
    finished = Signal(str, str)
    elapsed = Signal(int)
    warning = Signal(str)

    def __init__(self, capture, parent=None):
        super().__init__(parent)
        self.capture = capture
        self.active = False
        self.finalizing = False
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.timeout.connect(self.frame)

    def start(self, folder, system_audio=True, microphone=False, width=1280, height=720, fps=20):
        from .auth_gate import require_authorized
        require_authorized()
        if self.active or self.finalizing:
            raise RuntimeError('이미 녹화 중이거나 저장 중입니다.')
        self.width, self.height, self.fps = width, height, fps
        first = self.bytes(self.capture(width, height))  # Validate before creating files or opening audio devices.
        Path(folder).mkdir(parents=True, exist_ok=True)
        self.output = Path(folder)/f'수업녹화_{datetime.now():%Y%m%d_%H%M%S_%f}.mp4'
        self.workspace = Path(tempfile.mkdtemp(prefix='.ssen-recording-', dir=folder))
        self.frames = queue.Queue(maxsize=2)
        self.stop_event = threading.Event()
        self.tracks = []
        self.pa = None
        self.audio_files = []
        try:
            if system_audio or microphone:
                import pyaudiowpatch as p
                self.pa = p.PyAudio()
                if system_audio:
                    device = self.pa.get_default_wasapi_loopback()
                    self.tracks.append(AudioTrack(device, self.workspace/'system.wav', self.pa))
                if microphone:
                    device = self.pa.get_default_input_device_info()
                    self.tracks.append(AudioTrack(device, self.workspace/'mic.wav', self.pa))
            self.log = open(self.workspace/'encoder.log', 'wb')
            self.child = subprocess.Popen([ffmpeg(), '-hide_banner', '-loglevel', 'error', '-y',
                '-f', 'rawvideo', '-pixel_format', 'bgra', '-video_size', f'{width}x{height}',
                '-framerate', str(fps), '-i', 'pipe:0', '-an', '-c:v', 'libx264',
                '-preset', 'ultrafast', '-crf', '23', '-pix_fmt', 'yuv420p',
                str(self.workspace/'video.mkv')], stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL, stderr=self.log, **process_options())
            self.started = time.monotonic()
            for track in self.tracks: track.start()
            self.active = True
            self.frames.put(first)
            self.thread = threading.Thread(target=self.encode, daemon=True)
            self.thread.start()
            self.timer.start(round(1000/fps))
        except Exception:
            for track in self.tracks:
                try: track.stop()
                except Exception: pass
            if self.pa: self.pa.terminate()
            if getattr(self, 'child', None) and self.child.poll() is None:
                self.child.kill()
                self.child.wait()
            if getattr(self, 'log', None): self.log.close()
            shutil.rmtree(self.workspace, ignore_errors=True)
            raise

    def bytes(self, image):
        # Sources paint at the recording size; RGB32 is BGRA in memory on Windows (little-endian).
        if image.size() != QSize(self.width, self.height):
            image = image.scaled(self.width, self.height, Qt.IgnoreAspectRatio, Qt.FastTransformation)
        return bytes(image.convertToFormat(QImage.Format_RGB32).constBits())

    def frame(self):
        if not self.active: return
        try:
            if not self.frames.full(): self.frames.put_nowait(self.bytes(self.capture(self.width, self.height)))
            self.elapsed.emit(int(time.monotonic()-self.started))
        except Exception as error:
            self.warning.emit('녹화 프레임 오류: '+str(error))
            self.stop()

    def stop(self):
        if not self.active: return
        self.timer.stop()
        self.duration = max(.1, time.monotonic()-self.started)
        self.active = False
        self.finalizing = True
        self.stop_event.set()

    def encode(self):
        success, error = '', ''
        try:
            current = self.frames.get(timeout=5)
            count = 0
            while True:
                target = max(1, round((self.duration if self.stop_event.is_set() else time.monotonic()-self.started)*self.fps))
                while True:
                    try: current = self.frames.get_nowait()
                    except queue.Empty: break
                while count < target:
                    self.child.stdin.write(current)
                    count += 1
                if self.stop_event.is_set(): break
                self.stop_event.wait(1/self.fps/2)
            self.child.stdin.close()
            if self.child.wait(timeout=30):
                raise RuntimeError('영상 인코딩에 실패했습니다.')
            for track in self.tracks:
                track.stop()
                if track.path.stat().st_size > 44: self.audio_files.append(track.path)
            self.tracks = []
            if self.pa:
                self.pa.terminate()
                self.pa = None
            args = ['-y', '-i', str(self.workspace/'video.mkv')]
            for path in self.audio_files: args += ['-i', str(path)]
            if self.audio_files:
                sources = ''.join(f'[{i+1}:a]' for i in range(len(self.audio_files)))
                mix = sources + f'amix=inputs={len(self.audio_files)}:duration=longest:normalize=0,alimiter=limit=0.95,apad[a]'
                args += ['-filter_complex', mix, '-map', '0:v', '-map', '[a]', '-c:a', 'aac', '-b:a', '160k']
            else:
                args += ['-map', '0:v', '-an']
            args += ['-c:v', 'copy', '-t', str(count/self.fps), '-movflags', '+faststart', str(self.output)]
            run_ffmpeg(args)
            success = str(self.output)
        except Exception as exception:
            error = str(exception)
            self.output.unlink(missing_ok=True)
        finally:
            for track in self.tracks:
                try: track.stop()
                except Exception: pass
            if self.pa:
                try: self.pa.terminate()
                except Exception: pass
            if self.child.poll() is None:
                self.child.kill()
                self.child.wait()
            self.log.close()
            # Preserve intermediate video on failure so a lesson can be recovered.
            if not error: shutil.rmtree(self.workspace, ignore_errors=True)
            else: error += '\n복구용 파일: '+str(self.workspace)
            self.active = False
            self.finalizing = False
            self.finished.emit(success, error)
