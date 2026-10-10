"""Family-app buttons with bundled Phosphor icons and touch targets."""
from functools import lru_cache
from PySide6.QtCore import Qt, QSize, QByteArray
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QPushButton
from .media_tools import resource

ICONS = {'파일 열기':'folder-open','YouTube':'youtube-logo','재생 목록':'list-bullets',
    '설정':'sliders-horizontal','선택':'cursor','펜':'pen','형광펜':'highlighter',
    '지우개':'eraser','되돌리기':'arrow-counter-clockwise','다시 실행':'arrow-clockwise',
    '모두 지우기':'trash','캡처 저장':'camera','저장 폴더':'folder-open',
    '전체 화면':'corners-out','완전 화면':'corners-out','창 모드':'corners-in',
    '이전':'skip-back','다음':'skip-forward','−5초':'rewind','+5초':'fast-forward',
    '재생':'play','일시 정지':'pause','한 편 반복':'repeat','음소거':'speaker-high',
    '소리 켜기':'speaker-slash','여기부터':'bookmark-simple','여기까지':'bookmark-simple',
    '반복 해제':'repeat','구간 설정':'scissors','수업 녹화':'record','수업 도구 보기':'pen'}

@lru_cache(maxsize=100)
def icon(name, primary=False):
    svg = resource('assets/icons/'+name+'.svg').read_text('utf-8')
    result = QIcon()
    for state, color in [(QIcon.Off, '#ffffff' if primary else '#006241'), (QIcon.On, '#ffffff')]:
        data = svg.replace('currentColor',color)
        renderer = QSvgRenderer(QByteArray(data.encode()))
        for size in (20,40):
            pixmap = QPixmap(size,size)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            result.addPixmap(pixmap,QIcon.Normal,state)
    return result

class ActionButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setIconSize(QSize(20,20))
        self.setText(text)

    def setText(self, text):
        super().setText(text)
        self.setAccessibleName(text)
        key = '수업 녹화' if text.startswith('녹화 ') else text
        if key in ICONS:
            self.setIcon(icon(ICONS[key], self.objectName() == 'primary'))

def button(text, callback, name=None, tip=None):
    b = ActionButton(text)
    if name:
        b.setObjectName(name)
        b.setText(text)
    b.clicked.connect(callback)
    if tip: b.setToolTip(tip)
    return b

def icon_only(b):
    label = b.text()
    b.setToolTip(b.toolTip() or label)
    QPushButton.setText(b, '')
    b.setAccessibleName(label)
    b.setObjectName('iconButton')
    b.setFixedSize(44,44)
    return b
