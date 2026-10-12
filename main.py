import os
import sys
import time
from pathlib import Path

os.environ['QT_MEDIA_BACKEND'] = 'ffmpeg'
BUILD_TAG = '8574db8adac9'
STARTED = time.perf_counter()

def main():
    from app.identity import set_taskbar_identity
    set_taskbar_identity()
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFontDatabase, QIcon
    from app.player import Player
    from app.style import STYLE
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    application = QApplication(sys.argv)
    application.setApplicationName('SsenPlayer')
    application.setOrganizationName('HooniKim')
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
    QFontDatabase.addApplicationFont(str(base/'assets/Ghanachocolate.ttf'))
    # PNG loading is built into Qt; runtime branding must not depend on qico.dll.
    app_icon = QIcon(str(base/'assets/icon.png'))
    application.setWindowIcon(app_icon)
    application.setStyle('Fusion')
    application.setStyleSheet(STYLE)
    window = Player()
    window.setWindowIcon(app_icon)
    window.show()
    args = list(sys.argv[1:])
    diagnostics = None
    features = None
    if '--feature-test-output' in args:
        index = args.index('--feature-test-output')
        features = args[index+1]
        del args[index:index+2]
    if '--smoke-test-output' in args:
        index = args.index('--smoke-test-output')
        diagnostics = args[index+1]
        del args[index:index+2]
    paths = [p for p in args if not p.startswith('--') and Path(p).is_file()]
    if paths: window.add_files(paths)
    if diagnostics:
        from app.diagnostics import run
        run(application, window, Path(diagnostics), STARTED)
    if features:
        from app.feature_diagnostics import run
        run(application, window, Path(features))
    if not diagnostics and not features:
        from PySide6.QtCore import QTimer
        def check_update():
            window.offer_default_app()
            from app.updater import check_in_background
            check_in_background(window)
        QTimer.singleShot(3000, check_update)
    return application.exec()

if __name__ == '__main__':
    raise SystemExit(main())
