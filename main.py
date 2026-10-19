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
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    application = QApplication(sys.argv)
    application.setApplicationName('SsenPlayer')
    application.setOrganizationName('HooniKim')
    args = list(sys.argv[1:])
    # Diagnostic runs remain isolated from the user's interactive player.
    diagnostic_flags = ('--auth-test-output', '--feature-test-output', '--smoke-test-output')
    instance = None
    pending = []
    if not any(flag in args for flag in diagnostic_flags):
        from app.single_instance import SingleInstance
        from PySide6.QtWidgets import QMessageBox
        instance = SingleInstance(application)
        instance.files_received.connect(pending.append)
        paths = [str(Path(p).resolve()) for p in args if not p.startswith('--') and Path(p).is_file()]
        try:
            if not instance.start(paths):
                return 0
        except RuntimeError as error:
            QMessageBox.warning(None, '쎈플레이어', str(error))
            return 1
        application.aboutToQuit.connect(instance.close)
    from app.player import Player
    from app.style import STYLE
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
    from app.theme import load_fonts
    load_fonts()
    # PNG loading is built into Qt; runtime branding must not depend on qico.dll.
    app_icon = QIcon(str(base/'assets/icon.png'))
    application.setWindowIcon(app_icon)
    application.setStyle('Fusion')
    application.setStyleSheet(STYLE)
    auth_diagnostics = None
    if '--auth-test-output' in args:
        index = args.index('--auth-test-output')
        auth_diagnostics = Path(args[index+1])
        del args[index:index+2]
        from app.auth_diagnostics import create_window
        window = create_window(auth_diagnostics)
    else:
        window = Player()
    window.setWindowIcon(app_icon)
    window.show()
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
    if instance:
        instance.files_received.disconnect(pending.append)
        instance.files_received.connect(window.receive_files)
        for received in pending:
            window.receive_files(received)
    if diagnostics:
        from app.diagnostics import run
        run(application, window, Path(diagnostics), STARTED)
    if features:
        from app.feature_diagnostics import run
        run(application, window, Path(features))
    if auth_diagnostics:
        from app.auth_diagnostics import run as run_auth
        run_auth(application, window, auth_diagnostics)
    if not diagnostics and not features and not auth_diagnostics:
        from PySide6.QtCore import QTimer
        def check_update():
            window.offer_default_app()
            from app.updater import check_in_background
            check_in_background(window)
        QTimer.singleShot(3000, check_update)
    return application.exec()

if __name__ == '__main__':
    raise SystemExit(main())
