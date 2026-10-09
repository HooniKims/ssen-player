import os
import sys
import time
from pathlib import Path

os.environ['QT_MEDIA_BACKEND'] = 'ffmpeg'
STARTED = time.perf_counter()

def main():
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QFontDatabase, QIcon
    from app.player import Player
    from app.style import STYLE
    application = QApplication(sys.argv)
    application.setApplicationName('SsenPlayer')
    application.setOrganizationName('HooniKim')
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
    QFontDatabase.addApplicationFont(str(base/'assets/Ghanachocolate.ttf'))
    application.setWindowIcon(QIcon(str(base/'assets/icon.ico')))
    application.setStyle('Fusion')
    application.setStyleSheet(STYLE)
    window = Player()
    window.show()
    args = list(sys.argv[1:])
    diagnostics = None
    if '--smoke-test-output' in args:
        index = args.index('--smoke-test-output')
        diagnostics = args[index+1]
        del args[index:index+2]
    paths = [p for p in args if not p.startswith('--') and Path(p).is_file()]
    if paths: window.add_files(paths)
    if diagnostics:
        from app.diagnostics import run
        run(application, window, Path(diagnostics), STARTED)
    return application.exec()

if __name__ == '__main__':
    raise SystemExit(main())
