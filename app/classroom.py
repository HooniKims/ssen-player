"""YouTube, reusable lesson segments and recording UI shared by both sources."""
import json
from pathlib import Path
from PySide6.QtCore import QTimer, QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QLineEdit,
    QDoubleSpinBox,QListWidget,QCheckBox,QMessageBox)
from .ink import Ink
from .controls import button

SPEEDS = [.5, .75, 1, 1.25, 1.5, 2]


class ClassroomFeatures:
    def setup_extensions(self):
        from .recording import Recorder
        self.recorder = Recorder(self.capture_image, self)
        self.recorder.finished.connect(self.recording_finished)
        self.recorder.elapsed.connect(lambda sec:self.record_button.setText(f'녹화 종료 {sec//60:02}:{sec%60:02}'))
        self.recorder.warning.connect(self.notify)
        self.close_after_recording = False
        self.header.layout().insertWidget(4, self.make_button('YouTube', self.open_youtube))
        side = self.tools_scroll.layout()
        side.insertWidget(1, self.make_button('구간 설정', self.show_segments))
        self.record_button = self.make_button('수업 녹화', self.show_recording)
        side.insertWidget(2, self.record_button)
        self.record_button.setToolTip('영상과 필기하는 과정을 MP4로 저장')

    @staticmethod
    def make_button(text, callback):
        return button(text, callback)

    def capture_image(self, width=1920, height=1080):
        source = self.youtube if self.source_kind == 'youtube' else self.canvas
        return source.capture(width, height)

    def current_position(self):
        return round(self.youtube.state.get('time',0)*1000) if self.source_kind == 'youtube' else self.media.position()

    def current_duration(self):
        return round(self.youtube.state.get('duration',0)*1000) if self.source_kind == 'youtube' else self.media.duration()

    def seek_to(self, value):
        if self.source_kind == 'youtube': self.youtube.command('seek', value/1000)
        else: self.media.setPosition(value)

    def resume_playback(self):
        if self.source_kind == 'youtube': self.youtube.command('play')
        else: self.media.play()

    def pause_playback(self):
        if self.source_kind == 'youtube': self.youtube.command('pause')
        else: self.media.pause()

    def set_speed(self, speed):
        if self.source_kind == 'youtube': self.youtube.command('speed', speed)
        else: self.media.setPlaybackRate(speed)

    def set_volume(self, value):
        self.audio.setVolume(value/100)
        if self.source_kind == 'youtube': self.youtube.command('volume', value)

    def refresh_ink(self):
        self.canvas.viewport().update()
        if self.youtube: self.youtube.overlay.update()

    def open_youtube(self):
        from .youtube_browser import YouTubeBrowser
        dialog = YouTubeBrowser(self, self.settings.value('youtube_blocking', True, type=bool))
        if dialog.exec() == QDialog.Accepted and dialog.identifier:
            identifier, blocking = dialog.identifier, dialog.blocking.isChecked()
            self.settings.setValue('youtube_blocking', blocking)
            QTimer.singleShot(0, lambda: self.load_youtube(identifier, blocking))
        dialog.deleteLater()

    def load_youtube(self, identifier, blocking=True):
        from .youtube_url import video_id
        identifier = video_id(identifier)
        if self.segment_dialog: self.segment_dialog.close()
        self.cancel_countdown()
        self.save_position()
        self.media.pause()
        if self.current: self.inks[self.current] = self.canvas.ink
        self.notify('YouTube 플레이어를 준비하고 있습니다…')
        if self.youtube is None:
            from .youtube import YouTubeSurface
            self.youtube = YouTubeSurface(self.canvas)
            self.youtube.stateChanged.connect(self.youtube_state)
            self.youtube.message.connect(self.notify)
            self.video_stack.addWidget(self.youtube)
        self.source_kind = 'youtube'
        self.youtube_initialized = False
        self.current = 'https://www.youtube.com/watch?v='+identifier
        self.canvas.ink = self.inks.get(self.current, Ink())
        self.canvas.subtitle = ''
        self.canvas.loaded = True
        self.a = self.b = None
        self.ab_button.setText('여기부터')
        self.filename.setText('YouTube · '+identifier)
        self.video_stack.setCurrentWidget(self.youtube)
        if self.youtube.blocker.enabled != blocking: self.youtube.set_blocking(blocking)
        self.youtube.load(identifier)
        self.youtube.sync_tool()
        self.notify('YouTube 연결 중 · 구간 설정에서 원하는 부분을 반복하거나 MP4로 저장할 수 있습니다.')

    def youtube_state(self, state):
        if self.source_kind != 'youtube': return
        if state.get('ready') and not self.youtube_initialized:
            self.youtube_initialized = True
            self.youtube.command('volume', round(self.audio.volume()*100))
            self.youtube.command('mute', self.audio.isMuted())
            self.youtube.command('speed', SPEEDS[self.speed.currentIndex()])
        from .player import stamp
        duration = self.current_duration()
        position = self.current_position()
        self.seek.setRange(0, max(1,duration))
        if not self.seek.isSliderDown(): self.seek.setValue(position)
        self.time.setText(f'{stamp(position)} / {stamp(duration)}')
        self.play_button.setText('일시 정지' if state.get('state') == 1 else '재생')
        if state.get('title'):
            self.filename.setText(state['title'])
            self.filename.setToolTip(state['title'])
        if self.loop and state.get('state') == 0:
            self.youtube.command('seek',0)
            self.youtube.command('play')

    def apply_loop(self, start, end):
        if not 0 <= start < end or end-start < 500:
            raise ValueError('반복 구간은 0.5초 이상으로 지정해 주세요.')
        duration = self.current_duration()
        if duration > 0 and end > duration:
            raise ValueError('끝 지점이 영상 길이를 넘습니다.')
        self.a, self.b = start, end
        self.ab_button.setText('반복 해제')
        if self.source_kind == 'youtube': self.youtube.command('loop',[start/1000,end/1000])
        else:
            self.media.setPosition(start)
            self.media.play()
        self.notify(f'{start/1000:.1f}초부터 {end/1000:.1f}초까지 반복합니다.')

    def clear_loop(self):
        self.a = self.b = None
        self.ab_button.setText('여기부터')
        if self.source_kind == 'youtube': self.youtube.command('loop',None)

    def segment_data(self):
        try:
            data = json.loads(self.settings.value('segments','{}'))
            return data if isinstance(data,dict) else {}
        except (TypeError, ValueError): return {}

    def show_segments(self):
        if self.segment_dialog:
            self.segment_dialog.raise_()
            self.segment_dialog.activateWindow()
            return
        if not self.current or self.current_duration() <= 0:
            self.notify('영상을 먼저 열어 주세요. YouTube 영상은 불러오기가 끝나야 구간을 정할 수 있습니다.')
            return
        dialog = QDialog(self)
        dialog.setWindowTitle('수업 구간 · 반복과 저장')
        dialog.setMinimumSize(570,510)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(22,22,22,22)
        layout.setSpacing(12)
        layout.addWidget(QLabel('여기부터 → 여기까지 → 반복 재생'))
        fields = []
        for label, initial in [('시작 (초)', self.a if self.a is not None else self.current_position()),
                               ('끝 (초)', self.b if self.b is not None else min(self.current_duration(),self.current_position()+30000))]:
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            spin = QDoubleSpinBox()
            spin.setDecimals(1)
            spin.setRange(0,self.current_duration()/1000)
            spin.setSingleStep(.5)
            spin.setValue(initial/1000)
            spin.setMinimumHeight(44)
            row.addWidget(spin,1)
            row.addWidget(self.make_button('현재 위치',lambda _,s=spin:s.setValue(self.current_position()/1000)))
            layout.addLayout(row)
            fields.append(spin)
        message = QLabel('시작과 끝을 정한 뒤 반복 재생을 누르세요.')
        message.setWordWrap(True)
        layout.addWidget(message)
        def values():
            a,b=[round(s.value()*1000) for s in fields]
            if b-a < 500: raise ValueError('끝 지점은 시작보다 0.5초 이상 뒤여야 합니다.')
            return a,b
        def play():
            try:
                a,b=values()
                self.apply_loop(a,b)
                message.setText(f'{a/1000:.1f}–{b/1000:.1f}초 반복 중. 창을 닫아도 반복됩니다.')
            except ValueError as error: message.setText(str(error))
        row=QHBoxLayout()
        row.addWidget(self.make_button('반복 재생',play))
        row.addWidget(self.make_button('반복 해제',lambda:(self.clear_loop(),message.setText('반복을 해제했습니다.'))))
        layout.addLayout(row)
        name=QLineEdit()
        name.setPlaceholderText('구간 이름 · 예: 실험 결과, 발음 연습')
        layout.addWidget(name)
        saved=QListWidget()
        data=self.segment_data()
        entries=list(data.get(self.current,[]))
        def refresh():
            saved.clear()
            for entry in entries: saved.addItem(f"{entry['name']}   {entry['a']/1000:.1f}–{entry['b']/1000:.1f}초")
        def persist():
            data[self.current]=entries[-100:]
            self.settings.setValue('segments',json.dumps(data,ensure_ascii=False))
            self.settings.sync()
            refresh()
        def save():
            if not self.require_edit(): return
            try:
                a,b=values()
                entries.append(dict(name=name.text().strip() or f'구간 {len(entries)+1}',a=a,b=b))
                persist()
                message.setText('구간을 저장했습니다. 다음 수업에도 이 영상의 구간 목록에서 찾을 수 있습니다.')
            except ValueError as error: message.setText(str(error))
        def recall(item):
            entry=entries[saved.row(item)]
            fields[0].setValue(entry['a']/1000)
            fields[1].setValue(entry['b']/1000)
            name.setText(entry['name'])
            play()
        def remove():
            if not self.require_edit(): return
            if 0 <= saved.currentRow() < len(entries):
                entries.pop(saved.currentRow())
                persist()
        row=QHBoxLayout()
        row.addWidget(self.make_button('구간 목록에 저장',save))
        row.addWidget(self.make_button('선택 구간 삭제',remove))
        layout.addLayout(row)
        refresh()
        saved.itemClicked.connect(recall)
        layout.addWidget(saved,1)
        def export():
            if not self.require_edit(): return
            from .auth_gate import issue_permit
            try: a,b=values()
            except ValueError as error:
                message.setText(str(error))
                return
            from .clips import ClipDialog
            ClipDialog(dialog,self.current,a/1000,b/1000,self.capture_dir,self.source_kind=='youtube', permit=issue_permit('clip')).exec()
        layout.addWidget(self.make_button('이 구간을 MP4로 저장 · 필기 제외',export))
        layout.addWidget(self.make_button('닫고 영상 보기',dialog.accept))
        dialog.setModal(False)
        # Keep playback controls reachable while marking the current scene.
        dialog.setAttribute(Qt.WA_DeleteOnClose)
        dialog.finished.connect(lambda _:setattr(self,'segment_dialog',None))
        dialog.show()
        self.segment_dialog=dialog

    def show_recording(self):
        if self.recorder.active:
            self.record_button.setEnabled(False)
            self.record_button.setText('녹화 저장 중…')
            self.notify('녹화를 종료하고 MP4로 저장하고 있습니다…')
            self.recorder.stop()
            return
        if self.recorder.finalizing: return
        if not self.require_edit(): return
        dialog=QDialog(self)
        dialog.setWindowTitle('수업 녹화')
        dialog.setMinimumWidth(510)
        layout=QVBoxLayout(dialog)
        layout.setContentsMargins(22,22,22,22)
        layout.setSpacing(14)
        layout.addWidget(QLabel('영상과 필기하는 과정을 함께 MP4로 저장합니다.'))
        layout.addWidget(QLabel('720p · 20fps · 도구 모음 제외'))
        sound=QCheckBox('시스템 소리 포함 · 다른 앱의 소리도 녹음됩니다')
        sound.setChecked(True)
        mic=QCheckBox('기본 마이크 소리 포함 · 교사 설명 녹음')
        layout.addWidget(sound)
        layout.addWidget(mic)
        label=QLabel('저장 위치: '+self.capture_dir)
        label.setWordWrap(True)
        layout.addWidget(label)
        def start():
            try:
                self.recorder.start(self.capture_dir,sound.isChecked(),mic.isChecked())
                self.record_button.setText('녹화 종료 00:00')
                self.record_button.setStyleSheet('background:#C23B22;color:white;')
                self.notify('수업 녹화 중 · 영상과 필기를 함께 녹화합니다.')
                dialog.accept()
            except Exception as error: label.setText('녹화를 시작하지 못했습니다: '+str(error))
        layout.addWidget(self.make_button('녹화 시작',start))
        layout.addWidget(self.make_button('취소',dialog.reject))
        dialog.exec()

    def recording_finished(self,path,error):
        self.recorder.timer.stop()
        self.record_button.setText('수업 녹화')
        self.record_button.setEnabled(True)
        self.record_button.setStyleSheet('')
        self.notify('녹화 저장 완료 · '+path if path else '녹화 저장 실패: '+error)
        if self.close_after_recording:
            if error: QMessageBox.warning(self,'녹화 저장 확인',error)
            self.close()
