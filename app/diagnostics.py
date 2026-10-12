"""Explicit release verification mode; not used during normal startup."""
import json
import time
from .legal import COPYRIGHT
from PySide6.QtCore import QTimer, QPointF


def run(application, window, output, started):
    output.mkdir(parents=True, exist_ok=True)
    report = {'window_ready_seconds': round(time.perf_counter()-started, 3), 'copyright': COPYRIGHT}
    timer = QTimer(window)
    attempts = 0
    def inspect():
        nonlocal attempts
        attempts += 1
        frame = window.canvas.video.videoSink().videoFrame()
        if not frame.isValid():
            if attempts < 100: return
            report['error'] = window.media.errorString() or 'No video frame after 10 seconds'
            (output/'packaged.json').write_text(json.dumps(report, indent=2), 'utf-8')
            timer.stop()
            application.exit(1)
            return
        timer.stop()
        window.media.pause()
        window.choose_tool('pen')
        window.canvas.stroke_begin(QPointF(600, 300))
        window.canvas.stroke_move(QPointF(1200, 700))
        window.canvas.stroke_end()
        window.canvas.capture().save(str(output/'packaged-capture.png'))
        window.grab().save(str(output/'packaged-window.png'))
        report.update(decoded=True, capture_with_ink=True, frame_width=frame.width(), frame_height=frame.height())
        from PySide6.QtWidgets import QApplication
        from .legal import LegalPanel, license_text
        report['license_readable'] = '이용약관' in license_text() and '김승현' in license_text()
        def inspect_terms():
            dialog = QApplication.activeModalWidget()
            panel = dialog.findChild(LegalPanel)
            dialog.grab().save(str(output/'settings-copyright.png'))
            panel.toggle.click()
            QApplication.processEvents()
            QApplication.processEvents()
            report['license_expands'] = panel.text.isVisible() and '김승현' in panel.text.toPlainText()
            dialog.grab().save(str(output/'settings-license.png'))
            panel.toggle.click()
            report['license_collapses'] = not panel.text.isVisible()
            dialog.accept()
        QTimer.singleShot(200, inspect_terms)
        window.show_settings()
        from .updater import UpdateDialog
        update = UpdateDialog(window)
        update.show()
        QApplication.processEvents()
        panel = update.findChild(LegalPanel)
        update.grab().save(str(output/'update-copyright.png'))
        panel.toggle.click()
        QApplication.processEvents()
        QApplication.processEvents()
        report['update_license_expands'] = panel.text.isVisible() and '김승현' in panel.text.toPlainText()
        update.grab().save(str(output/'update-license.png'))
        panel.toggle.click()
        QApplication.processEvents()
        report['update_license_collapses'] = not panel.text.isVisible()
        update.close()
        (output/'packaged.json').write_text(json.dumps(report, indent=2), 'utf-8')
        window.close()
        application.quit()
    timer.timeout.connect(inspect)
    timer.start(100)

ORIGIN_TAG = 'a361cc157008'
