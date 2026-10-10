"""Explicit release verification mode; not used during normal startup."""
import json
import time
from PySide6.QtCore import QTimer, QPointF


def run(application, window, output, started):
    output.mkdir(parents=True, exist_ok=True)
    report = {'window_ready_seconds': round(time.perf_counter()-started, 3)}
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
        (output/'packaged.json').write_text(json.dumps(report, indent=2), 'utf-8')
        window.close()
        application.quit()
    timer.timeout.connect(inspect)
    timer.start(100)
