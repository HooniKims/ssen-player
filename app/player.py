from .runtime import prepare
prepare()

import json
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import Qt, QUrl, QTimer, QSettings, QStandardPaths, Signal, QObject, QRunnable, QThreadPool
from PySide6.QtGui import QDesktopServices, QShortcut, QKeySequence, QFont
from PySide6.QtWidgets import (QMainWindow, QWidget, QFrame, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QSlider, QComboBox, QButtonGroup, QGridLayout, QDialog, QCheckBox,
    QListWidget, QScrollArea, QSizePolicy, QStackedWidget, QMessageBox)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from .canvas import Canvas
from .ink import Ink
from .subtitles import read_subtitles
from . import VERSION
from .classroom import ClassroomFeatures
from .controls import button, icon_only

MEDIA_FILTER = '동영상 (*.mov *.mp4 *.mkv *.avi *.webm *.m4v *.wmv *.flv *.ts *.mts *.m2ts *.mpg *.mpeg *.3gp);;오디오 (*.mp3 *.flac *.wav *.m4a *.ogg);;모든 파일 (*)'


def stamp(ms):
    seconds = max(0, int(ms)//1000)
    h, seconds = divmod(seconds, 3600)
    m, s = divmod(seconds, 60)
    return f'{h}:{m:02}:{s:02}' if h else f'{m:02}:{s:02}'


class Saved(QObject):
    done = Signal(str, str)


class SaveCapture(QRunnable):
    def __init__(self, image, path):
        super().__init__()
        self.image, self.path, self.signals = image, path, Saved()

    def run(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if not self.image.save(str(self.path), 'PNG'):
                raise OSError('PNG 파일을 저장하지 못했습니다. 폴더 권한과 여유 공간을 확인해 주세요.')
            self.signals.done.emit(str(self.path), '')
        except Exception as error:
            self.signals.done.emit('', str(error))


class Player(ClassroomFeatures, QMainWindow):
    def __init__(self, settings=None):
        super().__init__()
        font = self.font()
        font.setStyleStrategy(QFont.PreferAntialias | QFont.NoSubpixelAntialias)
        self.setFont(font)
        self.setWindowTitle('쎈player')
        self.resize(1280, 820)
        self.setMinimumSize(1050, 690)
        self.settings = settings or QSettings('HooniKim', 'SsenPlayer')
        default = str(Path(QStandardPaths.writableLocation(QStandardPaths.PicturesLocation)) / '쎈player')
        self.capture_dir = self.settings.value('capture_dir', default)
        self.mode = 'window'
        self.current = None
        self.source_kind = 'local'
        self.youtube = None
        self.segment_dialog = None
        self.queue = []
        self.inks = {}
        self.subtitles = []
        self.subtitle_delay = 0
        self.a = self.b = None
        self.loop = False
        self.pending_resume = 0
        self.jobs = set()
        self.audio = QAudioOutput(self)
        self.audio.setVolume(float(self.settings.value('volume', .7)))
        self.media = QMediaPlayer(self)
        self.media.setAudioOutput(self.audio)
        self.canvas = Canvas()
        self.media.setVideoOutput(self.canvas.video)
        self.canvas.togglePlayback.connect(self.toggle)
        self.canvas.fullscreenRequested.connect(self.cycle_fullscreen)
        self._build()
        self.setup_extensions()
        self.media.positionChanged.connect(self.position)
        self.media.durationChanged.connect(lambda n: self.seek.setRange(0, max(1, n)) if self.source_kind == 'local' else None)
        self.media.playbackStateChanged.connect(self.playback_state)
        self.media.errorOccurred.connect(lambda _, message: self.notify('재생 오류: ' + message))
        self.media.mediaStatusChanged.connect(self.media_status)
        self.canvas.video.videoSink().subtitleTextChanged.connect(self.embedded_subtitle)
        for key, action in [('Space', self.toggle), ('Ctrl+O', self.open_files), ('F11', self.cycle_fullscreen),
                            ('Escape', self.escape), ('Ctrl+S', self.capture), ('Ctrl+Z', self.undo),
                            ('Ctrl+Y', self.redo), ('Right', lambda: self.jump(5000)),
                            ('Left', lambda: self.jump(-5000)), ('P', lambda: self.choose_tool('pen')),
                            ('V', lambda: self.choose_tool('pointer'))]:
            QShortcut(QKeySequence(key), self, activated=action)
        self.save_timer = QTimer(self)
        self.save_timer.timeout.connect(self.save_position)
        self.save_timer.start(10000)
        self.setAcceptDrops(True)

    def _build(self):
        central = QWidget()
        self.setCentralWidget(central)
        self.layout = QVBoxLayout(central)
        self.layout.setContentsMargins(18, 10, 18, 12)
        self.layout.setSpacing(12)
        self.header = QFrame(objectName='header')
        row = QHBoxLayout(self.header)
        row.setContentsMargins(3, 0, 0, 0)
        row.addWidget(QLabel('쎈player', objectName='brand'))
        self.filename = QLabel('수업에 집중하는 영상 플레이어', objectName='muted')
        self.filename.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        row.addWidget(self.filename, 1)
        row.addWidget(button('파일 열기', self.open_files, 'primary', 'Ctrl+O · 여러 영상 선택'))
        row.addWidget(button('재생 목록', self.toggle_queue))
        row.addWidget(button('설정', self.show_settings))
        self.layout.addWidget(self.header)
        self.middle = QHBoxLayout()
        self.middle.setSpacing(12)
        self.queue_list = QListWidget()
        self.queue_list.setFixedWidth(235)
        self.queue_list.itemDoubleClicked.connect(lambda item: self.load(self.queue[self.queue_list.row(item)]))
        self.queue_list.hide()
        self.middle.addWidget(self.queue_list)
        self.video_stack = QStackedWidget()
        self.video_stack.addWidget(self.canvas)
        self.middle.addWidget(self.video_stack, 1)
        self.tools_scroll = QFrame(objectName='tools')
        self.tools_scroll.setFixedWidth(216)
        panel_layout = QVBoxLayout(self.tools_scroll)
        panel_layout.setContentsMargins(14, 14, 14, 14)
        panel_layout.setSpacing(8)
        options_scroll = QScrollArea()
        options_scroll.setWidgetResizable(True)
        options_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tools = QFrame(objectName='toolOptions')
        side = QVBoxLayout(self.tools)
        side.setContentsMargins(2, 4, 2, 4)
        side.setSpacing(7)
        label = QLabel('수업 도구', objectName='section')
        side.addWidget(label)
        self.tool_group = QButtonGroup(self)
        self.tool_buttons = {}
        tool_grid = QGridLayout()
        tool_grid.setSpacing(6)
        for name, text, tip in [('pointer', '선택', '영상 터치로 재생 / 일시 정지 · V'), ('pen', '펜', '영상 위에 필기 · P'),
                                ('marker', '형광펜', '반투명한 굵은 선으로 필기'), ('eraser', '지우개', '닿은 획 지우기')]:
            b = button(text, lambda _, n=name: self.choose_tool(n), tip=tip)
            b.setCheckable(True)
            b.setObjectName('tool')
            self.tool_group.addButton(b)
            self.tool_buttons[name] = b
            index = len(self.tool_buttons)-1
            tool_grid.addWidget(b,index//2,index%2)
        side.addLayout(tool_grid)
        self.tool_buttons['pointer'].setChecked(True)
        colors = QGridLayout()
        colors.setSpacing(5)
        self.colors = QButtonGroup(self)
        for i, color in enumerate(['#ffdf59', '#ff6565', '#55d9fc', '#ffffff', '#59dd91', '#151f1a']):
            b = button('', lambda _, c=color: setattr(self.canvas, 'color', c), 'color', color)
            b.setFixedSize(44, 44)
            b.setAccessibleName('펜 색상 ' + color)
            b.setCheckable(True)
            b.setStyleSheet(f'QPushButton {{background:{color}; border:2px solid #c6d3cb;}} QPushButton:checked {{border:3px solid #00754a;}}')
            self.colors.addButton(b)
            b.setChecked(i == 0)
            colors.addWidget(b, i//3, i%3)
        side.addLayout(colors)
        self.width_combo = QComboBox()
        self.width_combo.addItems(['가는 펜', '중간 펜', '굵은 펜'])
        self.width_combo.setCurrentIndex(1)
        self.width_combo.currentIndexChanged.connect(lambda i: setattr(self.canvas, 'width', [3, 6, 12][i]))
        side.addWidget(self.width_combo)
        edits = QHBoxLayout()
        edits.addWidget(icon_only(button('되돌리기', self.undo, tip='되돌리기 · Ctrl+Z')))
        edits.addWidget(icon_only(button('다시 실행', self.redo, tip='다시 실행 · Ctrl+Y')))
        edits.addWidget(icon_only(button('모두 지우기', self.clear_ink, tip='모두 지우기 · 되돌리기로 복원 가능')))
        side.addLayout(edits)
        side.addStretch()
        options_scroll.setWidget(self.tools)
        panel_layout.addWidget(options_scroll, 1)
        side = panel_layout
        self.capture_button = button('캡처 저장', self.capture, 'primary', '영상 + 필기를 PNG로 저장 · Ctrl+S')
        side.addWidget(self.capture_button)
        utilities = QHBoxLayout()
        utilities.setSpacing(6)
        utilities.addWidget(icon_only(button('저장 폴더', self.open_capture_dir)))
        self.full_button = button('전체 화면', self.cycle_fullscreen, tip='F11 · 수업 화면 → 완전 화면 → 창 모드')
        utilities.addWidget(self.full_button, 1)
        side.addLayout(utilities)
        self.window_button = button('창 모드', lambda: self.set_mode('window'))
        self.window_button.hide()
        side.addWidget(self.window_button)
        self.middle.addWidget(self.tools_scroll)
        self.layout.addLayout(self.middle, 1)
        self.footer = QFrame(objectName='footer')
        foot = QVBoxLayout(self.footer)
        foot.setContentsMargins(0, 0, 0, 0)
        track = QHBoxLayout()
        self.time = QLabel('00:00 / 00:00')
        self.time.setMinimumWidth(140)
        self.seek = QSlider(Qt.Horizontal)
        self.seek.setRange(0, 1)
        self.seek.setMinimumHeight(28)
        self.seek.sliderReleased.connect(lambda: self.seek_to(self.seek.value()))
        track.addWidget(self.time)
        track.addWidget(self.seek, 1)
        foot.addLayout(track)
        controls = QHBoxLayout()
        controls.setSpacing(8)
        controls.addWidget(icon_only(button('이전', lambda: self.next_file(-1))))
        controls.addWidget(button('−5초', lambda: self.jump(-5000)))
        self.play_button = button('재생', self.toggle, 'primary', 'Space')
        self.play_button.setMinimumWidth(70)
        controls.addWidget(self.play_button)
        controls.addWidget(button('+5초', lambda: self.jump(5000)))
        controls.addWidget(icon_only(button('다음', lambda: self.next_file(1))))
        self.speed = QComboBox()
        self.speed.addItems(['0.5×', '0.75×', '1.0×', '1.25×', '1.5×', '2.0×'])
        self.speed.setCurrentIndex(2)
        self.speed.setToolTip('재생 속도')
        self.speed.currentIndexChanged.connect(lambda i: self.set_speed([.5, .75, 1, 1.25, 1.5, 2][i]))
        controls.addWidget(self.speed)
        self.ab_button = button('여기부터', self.ab_repeat, tip='시작 장면에서 여기부터 → 끝 장면에서 여기까지')
        controls.addWidget(self.ab_button)
        self.loop_button = button('한 편 반복', self.toggle_loop)
        self.loop_button.setCheckable(True)
        controls.addWidget(self.loop_button)
        controls.addStretch()
        self.mute_button = button('음소거', self.toggle_mute)
        controls.addWidget(self.mute_button)
        self.volume = QSlider(Qt.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setFixedWidth(95)
        self.volume.setValue(round(self.audio.volume()*100))
        self.volume.setToolTip('음량')
        self.volume.valueChanged.connect(self.set_volume)
        controls.addWidget(self.volume)
        foot.addLayout(controls)
        self.layout.addWidget(self.footer)
        self.status = QLabel('영상 위에 필기하고 수업 장면을 캡처해 보세요.', objectName='status')
        self.status.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.layout.addWidget(self.status)
        self.pure_exit = button('수업 도구 보기', lambda: self.set_mode('classroom'), 'pureExit')
        self.pure_exit.setParent(self)
        self.pure_exit.hide()
        self.exit_timer = QTimer(self)
        self.exit_timer.setSingleShot(True)
        self.exit_timer.timeout.connect(self.pure_exit.hide)
        self.canvas.viewport().installEventFilter(self)

    def notify(self, text):
        self.status.setText(text)
        self.status.setToolTip(text)

    def open_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, '영상 열기', self.settings.value('last_dir', ''), MEDIA_FILTER)
        if paths:
            self.add_files(paths)

    def add_files(self, paths):
        paths = [str(Path(p).resolve()) for p in paths if Path(p).is_file()]
        for path in paths:
            if path not in self.queue:
                self.queue.append(path)
                self.queue_list.addItem(Path(path).name)
                self.queue_list.item(len(self.queue)-1).setToolTip(path)
        if paths:
            self.load(paths[0])

    def load(self, path):
        if not Path(path).is_file():
            self.notify('파일을 찾을 수 없습니다: ' + path)
            return
        self.save_position()
        if self.segment_dialog: self.segment_dialog.close()
        if self.current:
            self.inks[self.current] = self.canvas.ink
        if self.youtube: self.youtube.command('pause')
        self.source_kind = 'local'
        self.video_stack.setCurrentWidget(self.canvas)
        self.current = path
        self.canvas.ink = self.inks.get(path, Ink())
        self.canvas.loaded = True
        self.canvas.subtitle = ''
        self.subtitles = []
        self.subtitle_delay = 0
        self.a = self.b = None
        self.ab_button.setText('여기부터')
        self.filename.setText(Path(path).name)
        self.filename.setToolTip(path)
        self.setWindowTitle(Path(path).name + ' · 쎈player')
        self.settings.setValue('last_dir', str(Path(path).parent))
        if path in self.queue:
            self.queue_list.setCurrentRow(self.queue.index(path))
        positions = self._positions()
        self.pending_resume = positions.get(path, 0)
        self.media.setSource(QUrl.fromLocalFile(path))
        for suffix in ('.srt', '.smi', '.vtt'):
            sub = Path(path).with_suffix(suffix)
            if sub.is_file():
                try: self.subtitles = read_subtitles(sub)
                except ValueError as error: self.notify(str(error))
                break
        self.media.play()
        self.notify('영상을 여는 중입니다…')

    def _positions(self):
        try: return json.loads(self.settings.value('positions', '{}'))
        except (ValueError, TypeError): return {}

    def save_position(self):
        if self.source_kind == 'local' and self.current and self.media.duration() > 0:
            positions = self._positions()
            positions.pop(self.current, None)
            position = self.media.position()
            positions[self.current] = position if position < self.media.duration()-3000 else 0
            self.settings.setValue('positions', json.dumps(dict(list(positions.items())[-100:])))

    def toggle(self):
        if self.source_kind == 'youtube':
            self.youtube.command('toggle')
            return
        if not self.current:
            self.open_files()
        elif self.media.playbackState() == QMediaPlayer.PlayingState:
            self.media.pause()
        else:
            self.media.play()

    def playback_state(self, state):
        if self.source_kind != 'local': return
        self.play_button.setText('일시 정지' if state == QMediaPlayer.PlayingState else '재생')

    def media_status(self, state):
        if self.source_kind != 'local': return
        if state == QMediaPlayer.LoadedMedia:
            if 0 < self.pending_resume < self.media.duration()-3000:
                self.media.setPosition(self.pending_resume)
            self.pending_resume = 0
            self.notify('재생 중에도 펜으로 쓸 수 있습니다. 캡처에는 영상과 필기가 함께 저장됩니다.')
        elif state == QMediaPlayer.EndOfMedia:
            if self.loop or (self.a is not None and self.b is not None):
                self.media.setPosition(self.a if self.a is not None and self.b is not None else 0)
                self.media.play()
            else:
                self.next_file(1, wrap=False)

    def position(self, value):
        if self.source_kind != 'local': return
        if not self.seek.isSliderDown(): self.seek.setValue(value)
        self.time.setText(f'{stamp(value)} / {stamp(self.media.duration())}')
        if self.b is not None and value >= self.b:
            self.media.setPosition(self.a)
        if self.subtitles:
            now = value-self.subtitle_delay
            text = '\n'.join(t for start, end, t in self.subtitles if start <= now < end)
            if text != self.canvas.subtitle:
                self.canvas.subtitle = text
                self.canvas.viewport().update()

    def embedded_subtitle(self, text):
        if not self.subtitles:
            self.canvas.subtitle = text
            self.canvas.viewport().update()

    def jump(self, delta):
        self.seek_to(max(0, min(self.current_duration(), self.current_position()+delta)))

    def next_file(self, delta, wrap=True):
        if not self.queue or self.current not in self.queue: return
        index = self.queue.index(self.current)+delta
        if not wrap and not 0 <= index < len(self.queue): return
        self.load(self.queue[index % len(self.queue)])

    def toggle_queue(self):
        self.queue_list.setVisible(not self.queue_list.isVisible())

    def choose_tool(self, name):
        self.canvas.set_tool(name)
        self.tool_buttons[name].setChecked(True)
        if self.youtube: self.youtube.sync_tool()

    def undo(self):
        self.canvas.ink.undo()
        self.refresh_ink()

    def redo(self):
        self.canvas.ink.redo()
        self.refresh_ink()

    def clear_ink(self):
        self.canvas.ink.clear()
        self.refresh_ink()
        self.notify('필기를 지웠습니다. 되돌리기 버튼으로 복원할 수 있습니다.')

    def capture(self):
        try:
            image = self.capture_image()
            name = ('YouTube_'+self.youtube.identifier) if self.source_kind == 'youtube' else (Path(self.current).stem if self.current else '수업')
            for char in '<>:"/\\|?*': name = name.replace(char, '_')
            name = name[:65]
            filename = f'{name}_{stamp(self.current_position()).replace(":", "-")}_{datetime.now():%Y%m%d_%H%M%S_%f}.png'
            job = SaveCapture(image, Path(self.capture_dir)/filename)
            self.jobs.add(job)
            job.signals.done.connect(lambda path, error, j=job: self.capture_done(j, path, error))
            QThreadPool.globalInstance().start(job)
            self.notify('영상과 필기를 함께 저장하고 있습니다…')
        except Exception as error:
            self.notify(str(error))

    def capture_done(self, job, path, error):
        self.jobs.discard(job)
        self.notify('저장 실패: ' + error if error else '캡처 저장 완료 · ' + path)

    def open_capture_dir(self):
        try:
            Path(self.capture_dir).mkdir(parents=True, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.capture_dir))
        except OSError as error:
            self.notify('폴더를 열지 못했습니다: '+str(error))

    def ab_repeat(self):
        if not self.current: return
        if self.a is None:
            self.a = self.current_position()
            self.ab_button.setText('여기까지')
            self.notify(f'시작 지점 {stamp(self.a)} 지정 · 끝 장면에서 여기까지를 눌러주세요.')
        elif self.b is None:
            if self.current_position() <= self.a+500:
                self.notify('끝 지점은 시작 지점보다 0.5초 이상 뒤에 지정해 주세요.')
                return
            self.apply_loop(self.a,self.current_position())
        else:
            self.clear_loop()

    def toggle_loop(self):
        self.loop = self.loop_button.isChecked()

    def toggle_mute(self):
        self.audio.setMuted(not self.audio.isMuted())
        if self.source_kind == 'youtube': self.youtube.command('mute',self.audio.isMuted())
        self.mute_button.setText('소리 켜기' if self.audio.isMuted() else '음소거')

    def cycle_fullscreen(self):
        self.set_mode({'window':'classroom', 'classroom':'pure', 'pure':'window'}[self.mode])

    def set_mode(self, mode):
        previous_mode = self.mode
        if self.mode == 'window' and mode != 'window':
            self.was_maximized = self.isMaximized()
        self.mode = mode
        self.header.setVisible(mode == 'window')
        self.footer.setVisible(mode != 'pure')
        self.tools_scroll.setVisible(mode != 'pure')
        self.status.setVisible(mode != 'pure')
        self.queue_list.hide()
        self.window_button.setVisible(mode == 'classroom')
        self.full_button.setText('완전 화면' if mode == 'classroom' else '전체 화면')
        margin = 0 if mode == 'pure' else 12
        self.layout.setContentsMargins(margin, margin, margin, margin)
        self.layout.setSpacing(0 if mode == 'pure' else 10)
        if mode == 'window':
            self.showMaximized() if getattr(self, 'was_maximized', False) else self.showNormal()
        else:
            self.showFullScreen()
        self.pure_exit.hide()
        if mode == 'pure':
            self.saved_tool = self.canvas.tool
            self.choose_tool('pointer')
            self.reveal_exit()
        elif previous_mode == 'pure':
            self.choose_tool(getattr(self, 'saved_tool', 'pointer'))
        QTimer.singleShot(0, lambda: self.canvas.fitInView(self.canvas.sceneRect(), Qt.KeepAspectRatio))

    def reveal_exit(self):
        self.pure_exit.adjustSize()
        self.pure_exit.move(self.width()-self.pure_exit.width()-20, 20)
        self.pure_exit.show()
        self.pure_exit.raise_()
        self.exit_timer.start(2500)

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if self.mode == 'pure' and event.type() in (QEvent.MouseMove, QEvent.MouseButtonPress, QEvent.TouchBegin):
            self.reveal_exit()
        return super().eventFilter(obj, event)

    def escape(self):
        if self.mode != 'window': self.set_mode('classroom' if self.mode == 'pure' else 'window')

    def show_settings(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('쎈player 설정')
        dialog.setMinimumWidth(540)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(14)
        layout.addWidget(QLabel('캡처·녹화·구간 저장 폴더'))
        folder = QLabel(self.capture_dir)
        folder.setWordWrap(True)
        layout.addWidget(folder)
        def change_folder():
            path = QFileDialog.getExistingDirectory(dialog, '캡처·녹화·구간 저장 폴더 선택', self.capture_dir)
            if path:
                self.capture_dir = path
                self.settings.setValue('capture_dir', path)
                folder.setText(path)
        layout.addWidget(button('저장 폴더 변경', change_folder))
        layout.addWidget(QLabel('자막과 음성'))
        layout.addWidget(button('자막 파일 열기 · SRT / SMI / VTT', self.open_subtitle))
        visible = QCheckBox('자막 표시')
        visible.setChecked(self.canvas.subtitle_visible)
        visible.toggled.connect(lambda value: (setattr(self.canvas, 'subtitle_visible', value), self.canvas.viewport().update()))
        layout.addWidget(visible)
        from PySide6.QtMultimedia import QMediaMetaData
        for title, tracks, active, setter in [('음성 트랙', self.media.audioTracks(), self.media.activeAudioTrack(), self.media.setActiveAudioTrack),
                                               ('내장 자막', self.media.subtitleTracks(), self.media.activeSubtitleTrack(), self.select_embedded_subtitle)]:
            if tracks:
                layout.addWidget(QLabel(title))
                combo = QComboBox()
                combo.addItem('끄기', -1)
                for i, meta in enumerate(tracks):
                    combo.addItem(meta.stringValue(QMediaMetaData.Title) or meta.stringValue(QMediaMetaData.Language) or f'트랙 {i+1}', i)
                combo.setCurrentIndex(active+1)
                combo.currentIndexChanged.connect(lambda i, s=setter: s(i-1))
                layout.addWidget(combo)
        delay = QHBoxLayout()
        delay.addWidget(QLabel('외부 자막 싱크'))
        delay.addWidget(button('−0.5초', lambda: self.shift_subtitle(-500)))
        delay.addWidget(button('+0.5초', lambda: self.shift_subtitle(500)))
        layout.addLayout(delay)
        layout.addWidget(QLabel(f'쎈player {VERSION} · HooniKim'))
        layout.addWidget(button('업데이트 확인', self.check_update))
        layout.addWidget(QLabel('F11  수업 / 완전 화면 전환    Esc  이전 화면\nCtrl+S  영상 + 필기 캡처    Ctrl+Z  필기 되돌리기', objectName='muted'))
        layout.addWidget(button('닫기', dialog.accept, 'primary'))
        dialog.exec()

    def select_embedded_subtitle(self, index):
        self.subtitles = []
        self.canvas.subtitle = ''
        self.media.setActiveSubtitleTrack(index)
        self.canvas.viewport().update()

    def shift_subtitle(self, delta):
        self.subtitle_delay += delta
        self.position(self.media.position())
        self.notify(f'외부 자막 싱크 {self.subtitle_delay/1000:+.1f}초')

    def open_subtitle(self):
        path, _ = QFileDialog.getOpenFileName(self, '자막 열기', '', '자막 (*.srt *.smi *.sami *.vtt)')
        if path:
            try:
                self.subtitles = read_subtitles(path)
                self.media.setActiveSubtitleTrack(-1)
                self.position(self.media.position())
                self.notify('자막을 불러왔습니다: ' + Path(path).name)
            except Exception as error: self.notify(str(error))

    def check_update(self):
        from .updater import UpdateDialog
        UpdateDialog(self).exec()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()

    def dropEvent(self, event):
        self.add_files([url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()])
        event.acceptProposedAction()

    def closeEvent(self, event):
        if self.recorder.active or self.recorder.finalizing:
            self.close_after_recording = True
            self.recorder.stop()
            self.notify('녹화를 저장한 뒤 종료합니다…')
            event.ignore()
            return
        if self.segment_dialog: self.segment_dialog.close()
        if self.youtube: self.youtube.shutdown()
        self.save_position()
        self.settings.setValue('volume', self.audio.volume())
        self.settings.sync()
        self.media.stop()
        QThreadPool.globalInstance().waitForDone(5000)
        super().closeEvent(event)
