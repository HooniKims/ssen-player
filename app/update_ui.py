"""Shared update presentation. Network, preferences and session state live in the controller."""
from datetime import datetime
from PySide6.QtCore import Qt, QObject, QEvent, QTimer
from PySide6.QtGui import QPainter, QColor
from PySide6.QtWidgets import (QPushButton, QLabel, QFrame, QDialog, QWidget, QVBoxLayout,
    QHBoxLayout, QScrollArea, QProgressBar, QCheckBox, QMessageBox, QSizePolicy)
from . import APP_NAME, VERSION
from .updater import highlights, plain_notes
from .theme import panel_shadow


def label(text='', name=''):
    widget = QLabel(text, objectName=name)
    widget.setTextFormat(Qt.PlainText)
    widget.setWordWrap(True)
    widget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
    widget.setTextInteractionFlags(Qt.TextSelectableByMouse)
    return widget


class UpdateButton(QPushButton):
    def event(self, event):
        if event.type() == QEvent.ShortcutOverride and event.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
            event.accept()
            return True
        return super().event(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.click()
            event.accept()
        else:
            super().keyPressEvent(event)


def action_button(text, callback, primary=False):
    widget = UpdateButton(text)
    widget.setMinimumHeight(38)
    widget.setCursor(Qt.PointingHandCursor)
    if primary: widget.setObjectName('primary')
    widget.clicked.connect(callback)
    return widget


def status_text(controller):
    return {'idle': '아직 확인하지 않았어요', 'checking': '업데이트 확인 중…',
            'current': '최신 버전이에요', 'available': '새 버전이 있어요',
            'downloading': '다운로드 중…', 'ready': '설치 준비가 끝났어요',
            'error': '오류가 발생했어요'}.get(controller.phase, '')


def size_text(controller):
    data = controller.payload or {}
    portable = controller.mode != 'installed'
    size = data.get('zip_size' if portable else 'size')
    kind = 'ZIP 파일' if portable else '설치 파일'
    return f'{kind} 약 {size / 1_000_000:,.1f}MB · 전체 파일 크기' if size else f'{kind} 크기를 확인할 수 없어요'


def action_text(controller):
    if controller.mode != 'installed': return '새 ZIP 받기'
    if controller.installer: return '재시작하여 설치'
    if controller.operation == 'downloading': return '다운로드 중…'
    return '업데이트'


class VersionButton(UpdateButton):
    def __init__(self, callback, parent=None):
        super().__init__(VERSION, parent)
        self.dot = False
        self.setFixedSize(64, 34)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setStyleSheet('QPushButton {min-height: 0; padding: 0 8px 0 0; border: none; color: #555; background: transparent;}'
                           'QPushButton:hover {background: #EAF6F0; border-radius: 6px;}'
                           'QPushButton:focus {border: 1px solid #00754A; border-radius: 6px;}')
        self.clicked.connect(callback)

    def refresh(self, controller):
        self.dot = controller.dot_visible
        state = ('새 버전 ' + controller.payload['version'] + ' 있음') if self.dot else status_text(controller)
        if controller.has_update and not self.dot: state = '새 버전 알림을 건너뛴 상태'
        text = f'{APP_NAME} 현재 버전 {VERSION} · {state} · 업데이트 안내 열기'
        self.setToolTip(text)
        self.setAccessibleName(text)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.dot:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor('#E34242'))
            painter.drawEllipse(self.width()-10, 3, 8, 8)


class UpdateCard(QFrame):
    def __init__(self, ui):
        super().__init__(ui.window)
        self.ui = ui
        self.setObjectName('updateCard')
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setStyleSheet('#updateCard {background: #EDF8F2; border: 1px solid #B5DCC9; border-radius: 14px;}'
                           '#updateCard QLabel {background: transparent; border: none;}'
                           '#updateCard QPushButton#skip {border: none; background: transparent; color: #496A5A; padding: 4px;}')
        panel_shadow(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 15, 18, 14)
        layout.setSpacing(10)
        row = QHBoxLayout()
        self.title = label('', 'section')
        row.addWidget(self.title, 1)
        self.close_button = action_button('×', ui.controller.dismiss)
        self.close_button.setAccessibleName('업데이트 알림 닫기')
        self.close_button.setFixedSize(28, 28)
        self.close_button.setStyleSheet('padding: 0; min-height: 0; font-family: Arial; font-size: 20px;')
        row.addWidget(self.close_button, 0, Qt.AlignTop)
        layout.addLayout(row)
        self.notes = label()
        layout.addWidget(self.notes)
        self.file_size = label('', 'muted')
        layout.addWidget(self.file_size)
        self.state = label()
        layout.addWidget(self.state)
        self.progress = QProgressBar()
        self.progress.setAccessibleName('업데이트 다운로드 진행률')
        layout.addWidget(self.progress)
        row = QHBoxLayout()
        self.action = action_button('업데이트', ui.act, True)
        row.addWidget(self.action, 1)
        self.later = action_button('나중에', ui.controller.dismiss)
        row.addWidget(self.later)
        layout.addLayout(row)
        self.skip = action_button('이 버전 건너뛰기', ui.skip)
        self.skip.setObjectName('skip')
        layout.addWidget(self.skip, 0, Qt.AlignLeft)
        self.hide()

    def refresh(self):
        c = self.ui.controller
        if not c.has_update: return
        self.title.setText(f"{APP_NAME} {c.payload['version']} 업데이트가 있어요")
        self.notes.setText('\n'.join('• ' + (text[:100] + '…' if len(text) > 100 else text)
                                     for text in highlights(plain_notes(c.payload.get('notes')))))
        self.file_size.setText(size_text(c))
        self.state.setText(c.error[:160] if c.error else status_text(c) if c.phase in ('ready', 'downloading') else '')
        self.state.setVisible(bool(self.state.text()))
        self.action.setText(action_text(c))
        self.action.setEnabled(not c.operation)
        self.skip.setEnabled(not c.operation)
        self.progress.setVisible(c.phase == 'downloading')
        self.progress.setValue(c.progress)


class UpdateDialog(QDialog):
    def event(self, event):
        if event.type() == QEvent.ShortcutOverride and event.key() == Qt.Key_Escape:
            event.accept()
            return True
        return super().event(event)

    def __init__(self, ui):
        super().__init__(ui.window)
        self.ui = ui
        self.setWindowTitle(f'{APP_NAME} 업데이트')
        self.setMinimumSize(480, 320)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 8, 12, 12)
        layout.setSpacing(14)
        self.scroll.setWidget(content)
        outer.addWidget(self.scroll)
        layout.addWidget(label(f'{APP_NAME} 업데이트', 'section'))
        self.summary = label()
        layout.addWidget(self.summary)
        self.error = label()
        self.error.setStyleSheet('color: #AC302D;')
        layout.addWidget(self.error)
        layout.addWidget(label('주요 변경 내용', 'section'))
        self.notes = label()
        layout.addWidget(self.notes)
        self.file_size = label('', 'muted')
        layout.addWidget(self.file_size)
        self.mode = label('', 'muted')
        layout.addWidget(self.mode)
        self.progress = QProgressBar()
        self.progress.setAccessibleName('업데이트 다운로드 진행률')
        layout.addWidget(self.progress)
        self.action = action_button('업데이트', ui.act, True)
        layout.addWidget(self.action)
        self.skip = action_button('이 버전 건너뛰기', ui.skip)
        layout.addWidget(self.skip)
        self.check = action_button('지금 확인', ui.controller.check)
        layout.addWidget(self.check)
        self.auto = QCheckBox('자동으로 확인하기')
        self.auto.toggled.connect(ui.controller.set_auto_check)
        layout.addWidget(self.auto)
        layout.addWidget(label('시작 15초 뒤, 4시간마다', 'muted'))
        layout.addWidget(label('업데이트 확인 때 주고받는 정보', 'section'))
        layout.addWidget(label('공식 GitHub 배포 서버에 최신 버전 정보와 릴리스 설명을 요청합니다. '
            '서버에는 IP 주소와 기본 HTTP 요청 정보가 전달됩니다. 현재 앱 버전은 기기 안에서 비교하며, '
            '계정·인증 정보, 영상·자막·필기 내용과 파일 경로는 보내지 않습니다. '
            '다운로드는 업데이트 버튼을 눌렀을 때만 시작합니다.', 'muted'))
        from .legal import LegalPanel
        layout.addWidget(LegalPanel())
        layout.addStretch()
        outer.addWidget(action_button('닫기', self.reject))
        self.refresh()

    def refresh(self):
        c = self.ui.controller
        try: checked = datetime.fromisoformat(c.last_checked).astimezone().strftime('%Y-%m-%d %H:%M:%S')
        except ValueError: checked = '아직 확인하지 않음'
        self.summary.setText(f'지금 버전    {VERSION}\n상태    {status_text(c)}\n마지막 확인    {checked}')
        self.error.setText(c.error)
        self.error.setVisible(bool(c.error))
        self.notes.setText(plain_notes((c.payload or {}).get('notes')) or '지금 확인을 눌러 릴리스 정보를 확인해 주세요.')
        self.file_size.setText(size_text(c))
        self.mode.setText('설치 후 앱이 다시 열립니다. 설치 전에는 저장 여부를 다시 확인합니다.' if c.mode == 'installed'
            else ('개발 실행에서는 설치하지 않습니다. ' if c.mode == 'development' else '') +
            '공식 배포 페이지에서 새 ZIP을 받아 압축을 푼 뒤 앱을 닫고 수동으로 교체해 주세요.')
        self.action.setText(action_text(c))
        self.action.setEnabled(c.has_update and not c.operation)
        self.skip.setVisible(c.has_update)
        self.skip.setText('이 버전은 건너뛰었어요' if c.has_update and c.skipped == c.payload['version'] else '이 버전 건너뛰기')
        self.skip.setEnabled(c.has_update and c.skipped != c.payload['version'] and not c.operation)
        self.check.setEnabled(not c.operation)
        self.auto.blockSignals(True)
        self.auto.setChecked(c.auto_check)
        self.auto.blockSignals(False)
        self.progress.setVisible(c.phase == 'downloading')
        self.progress.setValue(c.progress)


class UpdateUI(QObject):
    def __init__(self, window, controller):
        super().__init__(window)
        self.window, self.controller = window, controller
        self.card = UpdateCard(self)
        self.dialog = None
        window.installEventFilter(self)
        controller.changed.connect(self.refresh)
        self.refresh()

    def eventFilter(self, watched, event):
        if watched is self.window and event.type() in (QEvent.Resize, QEvent.Show, QEvent.WindowStateChange):
            QTimer.singleShot(0, self.refresh)
        return False

    def refresh(self):
        self.window.version_button.refresh(self.controller)
        if self.dialog: self.dialog.refresh()
        self.card.refresh()
        visible = self.controller.show_notice and self.window.mode == 'window'
        self.card.setVisible(visible)
        if visible:
            margin = min(24, self.window.width() // 20)
            self.card.setFixedWidth(min(360, self.window.width() - margin*2))
            self.card.setFixedHeight(self.card.layout().totalHeightForWidth(self.card.width()))
            self.card.move(self.window.width()-self.card.width()-margin,
                           max(margin, self.window.height()-self.card.height()-margin))
            self.card.raise_()

    def show_details(self):
        if self.dialog is None: self.dialog = UpdateDialog(self)
        available = self.window.screen().availableGeometry()
        self.dialog.resize(min(560, available.width()-48), min(740, self.window.height()-48, available.height()-80))
        self.dialog.refresh()
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()

    def skip(self):
        if not self.controller.skip(): self.show_details()

    def act(self):
        c = self.controller
        if c.installer and c.mode == 'installed':
            reason = c.busy_reason()
            if reason:
                c.fail(reason)
                self.show_details()
                return
            answer = QMessageBox.question(self.dialog if self.dialog and self.dialog.isVisible() else self.window,
                f'{APP_NAME} 업데이트 설치',
                '필요한 필기와 영상을 캡처·저장했나요?\n\n재시작하면 현재 재생 목록과 저장하지 않은 필기는 사라집니다. '
                '지금 앱을 닫고 업데이트를 설치할까요?', QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
            if answer == QMessageBox.Yes and not c.install(confirmed=True): self.show_details()
        else:
            c.action()
            if c.error: self.show_details()
