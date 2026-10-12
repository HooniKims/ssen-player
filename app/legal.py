"""App-owned terms; never included in user media or exported metadata."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit, QScrollArea
from PySide6.QtCore import QTimer
from .controls import button
from .media_tools import resource

COPYRIGHT = '© 2026 상명초 김승현, 등촌중 김형훈'


def license_text():
    return resource('LICENSE').read_text('utf-8')


class LegalPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        row = QHBoxLayout()
        row.setSpacing(4)
        label = QLabel(COPYRIGHT + ' ·')
        label.setStyleSheet('font-size:12px; color:#576d60;')
        row.addWidget(label)
        self.toggle = button('이용약관 보기', self.toggle_terms)
        self.toggle.setCheckable(True)
        self.toggle.setStyleSheet('QPushButton { background:transparent; border:0; border-radius:4px; padding:0 3px; min-height:36px; font-size:12px; color:#006241; text-decoration:underline; } QPushButton:hover { background:#e5f1eb; } QPushButton:focus { border:1px solid #00754a; }')
        row.addWidget(self.toggle)
        row.addStretch()
        layout.addLayout(row)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setAccessibleName('쎈player 이용약관 전문')
        self.text.setFixedHeight(260)
        self.text.setStyleSheet('QPlainTextEdit { background:#fafbf8; color:#183c30; border:1px solid #d6dfd6; border-radius:8px; padding:12px; font-size:12px; }')
        self.text.hide()
        layout.addWidget(self.text)

    def toggle_terms(self, checked):
        if checked and not self.text.toPlainText():
            self.text.setPlainText(license_text())
        self.text.setVisible(checked)
        self.toggle.setText('이용약관 닫기' if checked else '이용약관 보기')
        QTimer.singleShot(0, self.reveal_terms)

    def reveal_terms(self):
        parent = self.parentWidget()
        while parent is not None:
            if isinstance(parent, QScrollArea):
                if self.text.isVisible():
                    parent.ensureWidgetVisible(self.text, 0, 12)
                return
            parent = parent.parentWidget()
        self.window().adjustSize()

CREDITS_TAG = 'f7226d23fb54'
