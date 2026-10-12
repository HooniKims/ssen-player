"""Search YouTube in-app, then hand the chosen video to the lesson player."""
from urllib.parse import urlencode
from PySide6.QtCore import QUrl, QTimer, Signal
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QCheckBox
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from .controls import button
from .youtube_url import video_id


class SearchPage(QWebEnginePage):
    videoSelected = Signal(str)

    def acceptNavigationRequest(self, url, kind, main):
        if main:
            try:
                identifier = video_id(url.toString())
            except ValueError:
                pass
            else:
                self.videoSelected.emit(identifier)
                return False
        return url.scheme() in ('https', 'about')


class YouTubeBrowser(QDialog):
    def __init__(self, parent, blocking=True):
        super().__init__(parent)
        self.setWindowTitle('YouTube 검색')
        self.resize(1080, 760)
        self.identifier = None
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        self.field = QLineEdit()
        self.field.setPlaceholderText('검색어 또는 YouTube 영상 주소를 입력하세요')
        self.field.setAccessibleName('YouTube 검색어 또는 영상 주소')
        row.addWidget(self.field, 1)
        row.addWidget(button('검색 / 열기', self.search))
        layout.addLayout(row)
        self.hint = QLabel('영상을 선택하면 필기·캡처·구간 반복을 할 수 있는 재생 화면으로 열립니다.')
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)
        self.view = QWebEngineView(self)
        self.page = SearchPage(QWebEngineProfile.defaultProfile(), self.view)
        self.page.setAudioMuted(True)
        self.view.setPage(self.page)
        layout.addWidget(self.view, 1)
        self.blocking = QCheckBox('재생 시 광고 요청 차단 · 실험 기능')
        self.blocking.setChecked(blocking)
        layout.addWidget(self.blocking)
        self.page.videoSelected.connect(self.select_video)
        # YouTube also navigates via history.pushState without a new page request.
        self.view.urlChanged.connect(self.url_changed)
        self.view.loadFinished.connect(self.loaded)
        self.field.returnPressed.connect(self.search)
        self.finished.connect(lambda _: self.view.setUrl(QUrl('about:blank')))
        self.view.setUrl(QUrl('https://www.youtube.com/'))
        self.field.setFocus()

    def search(self):
        text = self.field.text().strip()
        if not text:
            self.field.setFocus()
            return
        try:
            if not text.lower().startswith(('https://', 'http://')):
                raise ValueError('Search term')
            identifier = video_id(text)
        except ValueError:
            self.hint.setText('검색 결과에서 재생할 영상을 선택하세요.')
            self.view.setUrl(QUrl('https://www.youtube.com/results?' + urlencode({'search_query': text})))
        else:
            self.select_video(identifier)

    def url_changed(self, url):
        try:
            identifier = video_id(url.toString())
        except ValueError:
            return
        self.select_video(identifier)

    def select_video(self, identifier):
        if self.identifier is not None:
            return
        self.identifier = identifier
        QTimer.singleShot(0, self.accept)

    def loaded(self, ok):
        if not ok and self.identifier is None:
            self.hint.setText('YouTube에 연결하지 못했습니다. 인터넷 연결을 확인하고 다시 검색해 주세요. 영상 주소를 넣어 열 수도 있습니다.')
