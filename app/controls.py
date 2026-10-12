"""Family-app buttons with bundled Phosphor icons and touch targets."""
from functools import lru_cache
from PySide6.QtCore import Qt, QSize, QRectF
from PySide6.QtGui import QIcon, QPainter, QPainterPath, QColor, QPen, QFontMetricsF
from PySide6.QtWidgets import QPushButton, QStyleOptionButton, QStyle
from .media_tools import resource

ICONS = {'파일 열기':'folder-open','YouTube':'youtube-logo','재생 목록':'list-bullets',
    '설정':'sliders-horizontal','선택':'cursor','펜':'pen','형광펜':'highlighter',
    '지우개':'eraser','되돌리기':'arrow-counter-clockwise','다시 실행':'arrow-clockwise',
    '모두 지우기':'trash','캡처 저장':'camera','저장 폴더':'folder-open',
    '전체 화면':'corners-out','완전 화면':'corners-out','창 모드':'corners-in',
    '이전':'skip-back','다음':'skip-forward','−5초':'rewind','+5초':'fast-forward',
    '재생':'play','일시 정지':'pause','한 편 반복':'repeat','음소거':'speaker-high',
    '소리 켜기':'speaker-slash','여기부터':'bookmark-simple','여기까지':'bookmark-simple',
    '반복 해제':'repeat','구간 설정':'scissors','수업 녹화':'record','수업 도구 보기':'pen',
    '5초 후 재생':'timer', '획 지우개':'eraser', '부분 지우개':'eraser',
    '닫기':'x','취소':'x','다음에':'x','나중에':'x','기본 앱 설정 열기':'sliders-horizontal','이용약관 보기':'file','이용약관 닫기':'file',
    '새 버전 확인':'arrow-clockwise','지금 업데이트':'download','업데이트 확인':'arrow-clockwise',
    '저장 폴더 변경':'folder-open','기본 동영상 앱으로 설정':'sliders-horizontal',
    '이용권':'check','센스쿨 계정':'check','무료 체험':'check','통합 이용권':'check',
    '검색 / 열기':'search','현재 위치':'bookmark-simple','녹화 시작':'record'}

@lru_cache(maxsize=100)
def icon(name, primary=False):
    result = QIcon()
    # SVG is the first source, so Qt selects its scalable SVG icon engine.
    # Do not cap the source at 20/40 raster pixels on high-DPI whiteboards.
    for state, color in [(QIcon.Off, 'white' if primary else 'green'), (QIcon.On, 'white' if primary else 'green')]:
        result.addFile(str(resource(f'assets/icons/{color}/{name}.svg')), QSize(), QIcon.Normal, state)
    return result

class ActionButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setIconSize(QSize(18,18))
        self.setText(text)

    def setText(self, text):
        super().setText(text)
        self.setAccessibleName(text)
        key = '수업 녹화' if text.startswith('녹화 ') else text
        symbol = ICONS.get(key)
        if symbol is None:
            symbol = ('folder-open' if '열기' in text else 'download' if '저장' in text else
                      'x' if '닫' in text or '삭제' in text else 'repeat' if '반복' in text else
                      'check' if '완료' in text else 'file')
        self.setIcon(icon(symbol, self.objectName() == 'primary' or text.startswith('녹화 종료')))

    def paintEvent(self, event):
        # Draw the supplied regular face with a thin outline, never synthetic bold.
        option = QStyleOptionButton()
        self.initStyleOption(option)
        option.text = ''
        option.icon = QIcon()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        self.style().drawControl(QStyle.CE_PushButton, option, painter, self)
        primary = self.objectName() == 'primary' or self.text().startswith('녹화 종료')
        color = QColor('#FFFFFF' if primary else '#006241' if self.isChecked() else '#1F1F1F')
        if not self.isEnabled(): color = QColor('#6B6B6B')
        fm = QFontMetricsF(self.font())
        text = self.text().replace('&', '')
        width = fm.horizontalAdvance(text)
        x = (self.width() - width - 25) / 2
        y = (self.height() - 18) / 2
        swatch = self.property('swatch')
        if swatch:
            painter.setPen(QPen(QColor('#D9D5CC'), 1))
            painter.setBrush(QColor(swatch))
            painter.drawRoundedRect(QRectF(x, y, 18, 18), 3, 3)
        else:
            self.icon().paint(painter, int(x), int(y), 18, 18, Qt.AlignCenter,
                              QIcon.Normal if self.isEnabled() else QIcon.Disabled,
                              QIcon.On if self.isChecked() else QIcon.Off)
        path = QPainterPath()
        path.addText(x + 25, (self.height() - fm.height()) / 2 + fm.ascent(), self.font(), text)
        painter.setBrush(color)
        painter.setPen(QPen(color, .4 if primary else .5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(path)

def button(text, callback, name=None, tip=None):
    b = ActionButton(text)
    if name:
        b.setObjectName(name)
        b.setText(text)
    b.clicked.connect(callback)
    if tip: b.setToolTip(tip)
    return b

def icon_only(b):
    # Compatibility for existing callers: all actions now retain visible labels.
    b.setToolTip(b.toolTip() or b.text())
    return b
