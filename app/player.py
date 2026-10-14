from .runtime import prepare
prepare()

import json
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import Qt, QUrl, QTimer, QSettings, QStandardPaths, Signal, QObject, QRunnable, QThreadPool, QEvent
from PySide6.QtGui import QDesktopServices, QShortcut, QKeySequence, QFont
from PySide6.QtWidgets import (QMainWindow, QWidget, QFrame, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QSlider, QComboBox, QButtonGroup, QGridLayout, QDialog, QCheckBox,
    QListWidget, QScrollArea, QSizePolicy, QStackedWidget, QApplication, QProxyStyle, QStyle,
    QPlainTextEdit)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from .canvas import Canvas
from .ink import Ink
from .subtitles import read_subtitles
from . import VERSION
from .classroom import ClassroomFeatures, SPEEDS
from .controls import button, icon_only
from .theme import load_fonts, panel_shadow
from .flow_layout import FlowLayout
from PySide6.QtSvgWidgets import QSvgWidget
from .media_tools import resource
from .auth_gate import ProtectedSettings, issue_permit, consume_permit, revoke_permits

COUNTDOWN_SECONDS = 5
MEDIA_FILTER = '동영상 (*.mov *.mp4 *.mkv *.avi *.webm *.m4v *.wmv *.flv *.ts *.mts *.m2ts *.mpg *.mpeg *.3gp);;오디오 (*.mp3 *.flac *.wav *.m4a *.ogg);;모든 파일 (*)'


def stamp(ms):
    seconds = max(0, int(ms)//1000)
    h, seconds = divmod(seconds, 3600)
    m, s = divmod(seconds, 60)
    return f'{h}:{m:02}:{s:02}' if h else f'{m:02}:{s:02}'


class TapToSeek(QProxyStyle):
    # A tap on the track jumps there; paging by one step is useless on a whiteboard.
    def styleHint(self, hint, option=None, widget=None, data=None):
        if hint == QStyle.SH_Slider_AbsoluteSetButtons:
            return Qt.LeftButton.value
        return super().styleHint(hint, option, widget, data)


class Saved(QObject):
    done = Signal(str, str)


class SaveCapture(QRunnable):
    def __init__(self, image, path, permit=None):
        super().__init__()
        self.image, self.path, self.signals = image, path, Saved()
        self.permit = permit

    def run(self):
        try:
            consume_permit(self.permit, 'capture')
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if not self.image.save(str(self.path), 'PNG'):
                raise OSError('PNG 파일을 저장하지 못했습니다. 폴더 권한과 여유 공간을 확인해 주세요.')
            self.signals.done.emit(str(self.path), '')
        except Exception as error:
            self.signals.done.emit('', str(error))


class Player(ClassroomFeatures, QMainWindow):
    def __init__(self, settings=None, auth_factory=None):
        super().__init__()
        font = self.font()
        font.setStyleStrategy(QFont.PreferAntialias | QFont.NoSubpixelAntialias)
        self.setFont(font)
        self.setWindowTitle('쎈Player')
        load_fonts()
        self.resize(1280, 800)
        self.setMinimumSize(1024, 700)
        self.settings = ProtectedSettings(settings or QSettings('HooniKim', 'SsenPlayer'))
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
        from .auth import AuthController
        self.auth = (auth_factory or AuthController)(self)
        QApplication.instance().auth_controller = self.auth
        self.auth.changed.connect(self.auth_changed)
        self.canvas.edit_guard = self.require_edit
        self.auth_button = button('이용권', lambda: self.auth.show())
        self.header.layout().insertWidget(self.header.layout().count()-1, self.auth_button)
        self.auth_notice = QLabel('이용권 확인 중…', objectName='authNotice')
        self.auth_notice.setWordWrap(True)
        self.root.insertWidget(1, self.auth_notice)
        QApplication.instance().aboutToQuit.connect(self.auth.shutdown)

    def require_edit(self):
        from .auth_gate import authorized
        if authorized(): return True
        auth = getattr(self, 'auth', None)
        if auth: auth.show()
        return False

    def auth_changed(self, state):
        ready, allowed = state.get('ready'), state.get('canEdit')
        plan = state.get('plan')
        label = {'edu_free': '센스쿨 계정', 'edu': '센스쿨 계정', 'trial': '무료 체험', 'licensed': '통합 이용권'}.get(plan, '이용권')
        self.auth_button.setText(label if allowed else '이용권')
        self.auth_notice.setText('이용권 확인 중…' if not ready else
            '작업 보호 모드 · 영상 열기와 재생은 계속 사용할 수 있습니다. 필기·저장은 이용권 인증 후 사용할 수 있습니다.')
        self.auth_notice.setVisible(not allowed and self.mode != 'pure')
        if ready and not allowed:
            revoke_permits()
            self.saved_tool = 'pointer'
            self.canvas.stroke_end()
            self.choose_tool('pointer')
            if self.recorder.active: self.show_recording()


    def _build(self):
        central = QWidget()
        self.setCentralWidget(central)
        self.root = QVBoxLayout(central)
        self.root.setContentsMargins(16, 0, 16, 12)
        self.root.setSpacing(14)
        self.header = QFrame(objectName='header')
        row = QHBoxLayout(self.header)
        self.header.setFixedHeight(72)
        row.setContentsMargins(12, 0, 12, 0)
        row.setSpacing(10)
        logo = QSvgWidget(str(resource('assets/logo.svg')))
        logo.setFixedSize(160, 34)
        logo.setAccessibleName('쎈Player')
        row.addWidget(logo)
        row.addWidget(QLabel(VERSION, objectName='muted'))
        self.filename = QLabel('수업에 집중하는 영상 플레이어', objectName='muted')
        self.filename.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        row.addWidget(self.filename, 1)
        row.addWidget(button('파일 열기', self.open_files, None, 'Ctrl+O · 여러 영상 선택'))
        row.addWidget(button('재생 목록', self.toggle_queue))
        row.addWidget(button('설정', self.show_settings))
        self.root.addWidget(self.header)
        self.middle = QHBoxLayout()
        self.middle.setSpacing(12)
        self.queue_panel = QFrame()
        self.queue_panel.setFixedWidth(250)
        queue_layout = QVBoxLayout(self.queue_panel)
        queue_layout.setContentsMargins(0, 0, 0, 0)
        queue_layout.addWidget(QLabel('재생 목록 · 위에서부터 순서대로'))
        queue_layout.addWidget(button('YouTube 링크 추가', self.open_youtube_links))
        self.queue_list = QListWidget()
        self.queue_list.itemDoubleClicked.connect(lambda item: self.load(self.queue[self.queue_list.row(item)]))
        queue_layout.addWidget(self.queue_list, 1)
        queue_actions = QHBoxLayout()
        queue_actions.addWidget(button('위로', lambda: self.move_queue_item(-1)))
        queue_actions.addWidget(button('아래로', lambda: self.move_queue_item(1)))
        queue_actions.addWidget(button('삭제', self.remove_queue_item))
        queue_layout.addLayout(queue_actions)
        self.queue_panel.hide()
        self.middle.addWidget(self.queue_panel)
        self.video_stack = QStackedWidget()
        self.video_stack.addWidget(self.canvas)
        self.middle.addWidget(self.video_stack, 1)
        self.tools_scroll = QFrame(objectName='tools')
        self.tools_scroll.setFixedWidth(260)
        panel_shadow(self.tools_scroll)
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
        tool_grid.setColumnStretch(0, 1)
        tool_grid.setColumnStretch(1, 1)
        for name, text, tip in [('pointer', '선택', '영상 터치로 재생 / 일시 정지 · V'), ('pen', '펜', '영상 위에 필기 · P'),
                                ('marker', '형광펜', '반투명한 굵은 선으로 필기'), ('eraser', '획 지우개', '닿은 획 전체 지우기'),
                                ('area_eraser', '부분 지우개', '문지른 부분만 지우기')]:
            b = button(text, lambda _, n=name: self.choose_tool(n), tip=tip)
            b.setCheckable(True)
            b.setObjectName('tool')
            self.tool_group.addButton(b)
            self.tool_buttons[name] = b
            index = len(self.tool_buttons)-1
            if name == 'pointer':
                tool_grid.addWidget(b, 0, 0, 1, 2)
            else:
                tool_grid.addWidget(b, 1 + (index-1)//2, (index-1)%2)
        side.addLayout(tool_grid)
        self.tool_buttons['pointer'].setChecked(True)
        colors = QGridLayout()
        colors.setSpacing(5)
        self.colors = QButtonGroup(self)
        for i, (name, color) in enumerate(zip(['노랑', '빨강', '하늘', '하양', '초록', '검정'], ['#ffdf59', '#ff6565', '#55d9fc', '#ffffff', '#59dd91', '#151f1a'])):
            b = button(name, lambda _, c=color: self.choose_color(c), 'color', color)
            b.setProperty('swatch', color)
            b.setAccessibleName('펜 색상 ' + color)
            b.setCheckable(True)
            self.colors.addButton(b)
            b.setChecked(i == 0)
            colors.addWidget(b, i//2, i%2)
        side.addLayout(colors)
        self.width_combo = QComboBox()
        self.width_combo.addItems(['가는 펜', '중간 펜', '굵은 펜'])
        self.width_combo.setCurrentIndex(1)
        self.width_combo.currentIndexChanged.connect(self.choose_width)
        side.addWidget(self.width_combo)
        self.eraser_size = QComboBox()
        self.eraser_size.addItems(['작은 지우개', '중간 지우개', '큰 지우개'])
        self.eraser_size.setCurrentIndex(1)
        self.eraser_size.setAccessibleName('부분 지우개 크기')
        self.eraser_size.currentIndexChanged.connect(lambda i: setattr(self.canvas, 'eraser_radius', [12, 24, 48][i]))
        self.eraser_size.hide()
        side.addWidget(self.eraser_size)
        edits = QVBoxLayout()
        edits.addWidget(icon_only(button('되돌리기', self.undo, tip='되돌리기 · Ctrl+Z')))
        edits.addWidget(icon_only(button('다시 실행', self.redo, tip='다시 실행 · Ctrl+Y')))
        edits.addWidget(icon_only(button('모두 지우기', self.clear_ink, tip='모두 지우기 · 되돌리기로 복원 가능')))
        side.addLayout(edits)
        side.addStretch()
        options_scroll.setWidget(self.tools)
        panel_layout.addWidget(options_scroll, 1)
        side = panel_layout
        self.capture_button = button('캡처 저장', self.capture, None, '영상 + 필기를 PNG로 저장 · Ctrl+S')
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
        self.root.addLayout(self.middle, 1)
        self.footer = QFrame(objectName='footer')
        foot = QVBoxLayout(self.footer)
        foot.setContentsMargins(16, 10, 16, 12)
        panel_shadow(self.footer)
        track = QHBoxLayout()
        self.time = QLabel('00:00 / 00:00')
        self.time.setMinimumWidth(140)
        self.seek_style = TapToSeek()
        self.seek = QSlider(Qt.Horizontal)
        self.seek.setStyle(self.seek_style)
        self.seek.setRange(0, 1)
        self.seek.setMinimumHeight(28)
        self.seek.sliderReleased.connect(lambda: self.seek_to(self.seek.value()))
        track.addWidget(self.time)
        track.addWidget(self.seek, 1)
        foot.addLayout(track)
        controls = FlowLayout()
        controls.setSpacing(8)
        controls.addWidget(icon_only(button('이전', lambda: self.next_file(-1))))
        controls.addWidget(button('−5초', lambda: self.jump(-5000)))
        self.play_button = button('재생', self.toggle, 'primary', 'Space')
        self.play_button.setMinimumWidth(70)
        controls.addWidget(self.play_button)
        self.countdown_button = icon_only(button('5초 후 재생', self.start_countdown,
            tip='5초 후 재생 · 화면의 5, 4, 3, 2, 1이 사라지는 순간 재생 · 다시 누르면 취소'))
        self.countdown_button.setCheckable(True)
        controls.addWidget(self.countdown_button)
        controls.addWidget(button('+5초', lambda: self.jump(5000)))
        controls.addWidget(icon_only(button('다음', lambda: self.next_file(1))))
        self.speed = QComboBox()
        self.speed.addItems(['0.5×', '0.75×', '1.0×', '1.25×', '1.5×', '2.0×'])
        self.speed.setCurrentIndex(2)
        self.speed.setToolTip('재생 속도')
        self.speed.currentIndexChanged.connect(lambda i: self.set_speed(SPEEDS[i]))
        controls.addWidget(self.speed)
        self.ab_button = button('여기부터', self.ab_repeat, tip='시작 장면에서 여기부터 → 끝 장면에서 여기까지')
        controls.addWidget(self.ab_button)
        self.loop_button = button('한 편 반복', self.toggle_loop)
        self.loop_button.setCheckable(True)
        controls.addWidget(self.loop_button)
        self.mute_button = button('음소거', self.toggle_mute)
        volume_group = QWidget()
        volume_row = QHBoxLayout(volume_group)
        volume_row.setContentsMargins(0, 0, 0, 0)
        volume_row.setSpacing(8)
        volume_row.addWidget(self.mute_button)
        self.volume = QSlider(Qt.Horizontal)
        self.volume.setStyle(self.seek_style)
        self.volume.setRange(0, 100)
        self.volume.setFixedWidth(95)
        self.volume.setValue(round(self.audio.volume()*100))
        self.volume.setToolTip('음량')
        self.volume.valueChanged.connect(self.set_volume)
        volume_row.addWidget(self.volume)
        controls.addWidget(volume_group)
        foot.addLayout(controls)
        self.root.addWidget(self.footer)
        self.status = QLabel('영상 위에 필기하고 수업 장면을 캡처해 보세요.', objectName='status')
        self.toast = QLabel(self, objectName='toast')
        self.toast.setWordWrap(True)
        self.toast.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.toast.hide()
        self.toast_timer = QTimer(self)
        self.toast_timer.setSingleShot(True)
        self.toast_timer.timeout.connect(self.toast.hide)
        self.status.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.root.addWidget(self.status)
        self.pure_exit = button('수업 도구 보기', lambda: self.set_mode('classroom'), 'pureExit')
        self.pure_exit.setParent(self)
        self.pure_exit.hide()
        self.exit_timer = QTimer(self)
        self.exit_timer.setSingleShot(True)
        self.exit_timer.timeout.connect(self.pure_exit.hide)
        # Shown over both the local canvas and the YouTube view; never blocks pen input.
        self.countdown_label = QLabel(self.video_stack, objectName='countdown')
        self.countdown_label.setAlignment(Qt.AlignCenter)
        self.countdown_label.setFixedSize(180, 180)
        self.countdown_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.countdown_label.hide()
        self.countdown_timer = QTimer(self)
        self.countdown_timer.setTimerType(Qt.PreciseTimer)
        self.countdown_timer.timeout.connect(self.countdown_tick)
        self.countdown_left = 0

    def notify(self, text):
        self.status.setText(text)
        self.status.setToolTip(text)
        self.toast.setText(text)
        self.toast.setFixedWidth(min(640, self.width() - 64))
        self.toast.adjustSize()
        self.toast.move((self.width() - self.toast.width()) // 2, self.height() - self.toast.height() - 26)
        self.toast.show()
        self.toast.raise_()
        self.toast_timer.start(4000)

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

    def open_youtube_links(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('YouTube 링크를 재생 목록에 추가')
        dialog.resize(580, 400)
        layout = QVBoxLayout(dialog)
        hint = QLabel('링크를 한 줄에 하나씩 붙여 넣으세요. 공백으로 구분해도 됩니다.\n입력한 순서대로 추가되며, 현재 재생은 계속됩니다.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        links = QPlainTextEdit()
        links.setPlaceholderText('https://www.youtube.com/watch?v=…\nhttps://youtu.be/…')
        layout.addWidget(links)
        feedback = QLabel('중복 영상은 한 번만 추가합니다. 목록은 앱을 닫으면 비워집니다.')
        feedback.setWordWrap(True)
        layout.addWidget(feedback)
        play = QCheckBox('추가한 첫 영상부터 바로 재생')
        layout.addWidget(play)
        def add():
            try:
                urls, count = self.add_youtube_links(links.toPlainText())
            except ValueError as error:
                feedback.setText(str(error))
                return
            dialog.accept()
            self.notify(f'YouTube 영상 {count}개를 재생 목록에 추가했습니다. 항목을 두 번 누르면 재생합니다.')
            if play.isChecked(): self.load(urls[0])
        actions = QHBoxLayout()
        actions.addWidget(button('취소', dialog.reject))
        actions.addWidget(button('목록에 추가', add))
        layout.addLayout(actions)
        dialog.exec()
        dialog.deleteLater()

    def add_youtube_links(self, text):
        from .youtube_url import video_urls, video_id
        urls = video_urls(text)
        count = 0
        for url in urls:
            if url in self.queue: continue
            self.queue.append(url)
            self.queue_list.addItem('YouTube · ' + video_id(url))
            self.queue_list.item(len(self.queue)-1).setToolTip(url)
            count += 1
        self.queue_panel.show()
        return urls, count

    def move_queue_item(self, delta):
        row = self.queue_list.currentRow()
        target = row + delta
        if not 0 <= row < len(self.queue) or not 0 <= target < len(self.queue): return
        self.queue.insert(target, self.queue.pop(row))
        item = self.queue_list.takeItem(row)
        self.queue_list.insertItem(target, item)
        self.queue_list.setCurrentRow(target)

    def remove_queue_item(self):
        row = self.queue_list.currentRow()
        if not 0 <= row < len(self.queue): return
        # Keep the playing item as the anchor for automatic next/previous.
        if self.queue[row] == self.current:
            self.notify('재생 중인 항목입니다. 다른 영상을 연 뒤 삭제해 주세요.')
            return
        self.queue.pop(row)
        self.queue_list.takeItem(row)

    def load(self, path):
        if path.startswith(('https://', 'http://')):
            self.load_youtube(path, self.settings.value('youtube_blocking', True, type=bool))
            return
        if not Path(path).is_file():
            self.notify('파일을 찾을 수 없습니다: ' + path)
            return
        self.save_position()
        self.cancel_countdown()
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
        self.setWindowTitle(Path(path).name + ' · 쎈Player')
        self.settings.setValue('last_dir', str(Path(path).parent))
        if path in self.queue:
            self.queue_list.setCurrentRow(self.queue.index(path))
        positions = self._positions()
        self.pending_resume = positions.get(path, 0)
        self.media.setSource(QUrl.fromLocalFile(path))
        # Speed may have changed while YouTube was playing; an unchanged source emits no durationChanged.
        self.media.setPlaybackRate(SPEEDS[self.speed.currentIndex()])
        self.seek.setRange(0, max(1, self.media.duration()))
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
        self.cancel_countdown()
        if self.source_kind == 'youtube':
            self.youtube.command('toggle')
            return
        if not self.current:
            self.open_files()
        elif self.media.playbackState() == QMediaPlayer.PlayingState:
            self.media.pause()
        else:
            self.media.play()

    def start_countdown(self):
        if self.countdown_timer.isActive():
            self.cancel_countdown()
            self.notify('카운트다운을 취소했습니다.')
            return
        self.countdown_button.setChecked(False)
        if not self.current:
            self.notify('영상을 먼저 열어 주세요.')
            return
        if self.source_kind == 'youtube' and not self.youtube.state.get('ready'):
            self.notify('YouTube 영상이 준비된 뒤 다시 눌러 주세요.')
            return
        self.pause_playback()
        self.countdown_left = COUNTDOWN_SECONDS
        self.show_countdown()
        self.countdown_button.setChecked(True)
        self.countdown_timer.start(1000)
        self.notify('숫자가 사라지는 0의 순간에 재생합니다. 녹화 프로그램의 시작 버튼을 그때 누르세요.')

    def countdown_tick(self):
        self.countdown_left -= 1
        if self.countdown_left > 0:
            self.show_countdown()
            return
        # Hide before playing so a screen recorder started at 0 never sees the number.
        self.cancel_countdown()
        self.resume_playback()
        self.notify('재생을 시작했습니다.')

    def show_countdown(self):
        self.countdown_label.setText(str(self.countdown_left))
        self.place_countdown()
        self.countdown_label.show()
        self.countdown_label.raise_()

    def place_countdown(self):
        label = self.countdown_label
        label.move((self.video_stack.width()-label.width())//2, (self.video_stack.height()-label.height())//2)

    def cancel_countdown(self):
        if not self.countdown_timer.isActive() and self.countdown_label.isHidden(): return
        self.countdown_timer.stop()
        self.countdown_label.hide()
        self.countdown_button.setChecked(False)

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
        self.queue_panel.setVisible(not self.queue_panel.isVisible())

    def choose_tool(self, name):
        if name != 'pointer' and not self.require_edit():
            self.tool_buttons[self.canvas.tool].setChecked(True)
            return
        self.canvas.set_tool(name)
        self.tool_buttons[name].setChecked(True)
        self.eraser_size.setVisible(name == 'area_eraser')
        self.width_combo.setVisible(name not in ('eraser', 'area_eraser'))
        if self.youtube: self.youtube.sync_tool()

    def choose_color(self, color):
        if not self.require_edit(): return
        self.canvas.color = color
        if self.canvas.tool not in ('pen', 'marker'): self.choose_tool('pen')

    def choose_width(self, index):
        if not self.require_edit(): return
        self.canvas.pen_width = [3, 6, 12][index]
        if self.canvas.tool not in ('pen', 'marker'): self.choose_tool('pen')

    def undo(self):
        if not self.require_edit(): return
        self.canvas.ink.undo()
        self.refresh_ink()

    def redo(self):
        if not self.require_edit(): return
        self.canvas.ink.redo()
        self.refresh_ink()

    def clear_ink(self):
        if not self.require_edit(): return
        self.canvas.ink.clear()
        self.refresh_ink()
        self.notify('필기를 지웠습니다. 되돌리기 버튼으로 복원할 수 있습니다.')

    def capture(self):
        if not self.require_edit(): return
        try:
            image = self.capture_image()
            name = ('YouTube_'+self.youtube.identifier) if self.source_kind == 'youtube' else (Path(self.current).stem if self.current else '수업')
            for char in '<>:"/\\|?*': name = name.replace(char, '_')
            name = name[:65]
            filename = f'{name}_{stamp(self.current_position()).replace(":", "-")}_{datetime.now():%Y%m%d_%H%M%S_%f}.png'
            job = SaveCapture(image, Path(self.capture_dir)/filename, issue_permit('capture'))
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
            if not Path(self.capture_dir).exists():
                if not self.require_edit(): return
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
        self.auth_notice.setVisible(mode != 'pure' and not self.auth.snapshot.get('canEdit'))
        self.footer.setVisible(mode != 'pure')
        self.tools_scroll.setVisible(mode != 'pure')
        self.status.setVisible(mode != 'pure')
        self.queue_panel.hide()
        self.window_button.setVisible(mode == 'classroom')
        self.full_button.setText('완전 화면' if mode == 'classroom' else '전체 화면')
        margin = 0 if mode == 'pure' else 12
        self.root.setContentsMargins(margin, margin, margin, margin)
        self.root.setSpacing(0 if mode == 'pure' else 10)
        if mode == 'window':
            self.showMaximized() if getattr(self, 'was_maximized', False) else self.showNormal()
        else:
            self.showFullScreen()
        self.pure_exit.hide()
        # Watch the whole app: on YouTube, touches land in the browser view, not the canvas.
        QApplication.instance().removeEventFilter(self)
        if mode == 'pure':
            QApplication.instance().installEventFilter(self)
            self.saved_tool = self.canvas.tool
            self.choose_tool('pointer')
            self.reveal_exit()
        elif previous_mode == 'pure':
            self.choose_tool(getattr(self, 'saved_tool', 'pointer'))
        QTimer.singleShot(0, lambda: self.canvas.fitInView(self.canvas.sceneRect(), Qt.KeepAspectRatio))
        QTimer.singleShot(0, self.place_countdown)

    def reveal_exit(self):
        self.pure_exit.adjustSize()
        self.pure_exit.move(self.width()-self.pure_exit.width()-20, 20)
        self.pure_exit.show()
        self.pure_exit.raise_()
        self.exit_timer.start(2500)

    def eventFilter(self, obj, event):
        if self.mode == 'pure' and event.type() in (QEvent.MouseMove, QEvent.MouseButtonPress, QEvent.TouchBegin, QEvent.TabletPress):
            self.reveal_exit()
        return super().eventFilter(obj, event)

    def escape(self):
        if self.mode != 'window': self.set_mode('classroom' if self.mode == 'pure' else 'window')

    def open_default_apps(self):
        if not self.require_edit(): return
        from .file_associations import register_player, SETTINGS_URI
        from PySide6.QtWidgets import QMessageBox
        try:
            register_player()
            if not QDesktopServices.openUrl(QUrl(SETTINGS_URI)):
                raise RuntimeError('Windows 설정을 열지 못했습니다. 설정 → 앱 → 기본 앱에서 쎈Player를 선택해 주세요.')
        except (OSError, RuntimeError) as error:
            QMessageBox.information(self, '기본 앱 설정', str(error))

    def default_app_dialog(self):
        from PySide6.QtWidgets import QMessageBox
        dialog = QMessageBox(self)
        dialog.setWindowTitle('기본 동영상 앱 설정')
        dialog.setText('동영상 파일을 더블클릭하면 쎈Player로 열까요?')
        dialog.setInformativeText('Windows 기본 앱 설정에서 쎈Player를 선택해 주세요. 나중에 설정에서 변경할 수도 있습니다.')
        setup = button('기본 앱 설정 열기', lambda: None)
        dialog.addButton(setup, QMessageBox.AcceptRole)
        dialog.later_button = button('나중에', lambda: None)
        dialog.addButton(dialog.later_button, QMessageBox.RejectRole)
        return dialog, setup

    def offer_default_app(self):
        import sys
        from .file_associations import is_default_player
        from PySide6.QtWidgets import QMessageBox
        if not self.auth.snapshot.get('canEdit'): return
        if not getattr(sys, 'frozen', False) or self.current or self.mode != 'window':
            return
        if self.settings.value('default_app_prompt_seen', False, type=bool) or is_default_player():
            return
        dialog, setup = self.default_app_dialog()
        self.settings.setValue('default_app_prompt_seen', True)
        dialog.exec()
        if dialog.clickedButton() == setup:
            self.open_default_apps()

    def show_settings(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('쎈Player 설정')
        dialog.setMinimumWidth(540)
        outer = QVBoxLayout(dialog)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        scroll.setWidget(content)
        outer.addWidget(scroll)
        dialog.resize(600, min(760, self.screen().availableGeometry().height() - 80))
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(14)
        layout.addWidget(button('기본 동영상 앱으로 설정', self.open_default_apps))
        layout.addWidget(QLabel('캡처·녹화·구간 저장 폴더'))
        folder = QLabel(self.capture_dir)
        folder.setWordWrap(True)
        layout.addWidget(folder)
        def change_folder():
            if not self.require_edit(): return
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
        layout.addWidget(QLabel(f'쎈Player {VERSION} · HooniKim'))
        layout.addWidget(button('업데이트 확인', self.check_update))
        layout.addWidget(QLabel('F11  수업 / 완전 화면 전환    Esc  이전 화면\nCtrl+S  영상 + 필기 캡처    Ctrl+Z  필기 되돌리기', objectName='muted'))
        from .legal import LegalPanel
        layout.addWidget(LegalPanel())
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

    def update_checked(self, payload, error):
        self.update_task = None
        if error or not payload: return  # Offline or nothing new: stay silent at startup.
        if self.mode != 'window' or self.recorder.active or self.recorder.finalizing:
            self.notify(f"새 버전 {payload['version']}이 나왔습니다. 설정 → 업데이트 확인에서 설치할 수 있습니다.")
            return
        from .updater import UpdateDialog
        UpdateDialog(self, payload).exec()

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
