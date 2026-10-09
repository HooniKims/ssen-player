"""Opt-in installed-binary integration check; uses a public YouTube demo."""
import json
import time
from PySide6.QtCore import QTimer, QPointF, QThreadPool
from app.clips import ClipJob


def run(application, window, output):
    output.mkdir(parents=True, exist_ok=True)
    report = {}
    began = time.monotonic()
    stage = 'web'
    timer = QTimer(window)

    def finish(error=''):
        timer.stop()
        report['error'] = error
        (output/'features.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), 'utf-8')
        window.close()
        application.exit(1 if error else 0)

    def clipped(path, error):
        report['clip'] = path
        finish(error)

    def recorded(path, error):
        nonlocal stage
        if error:
            finish(error)
            return
        report['recording'] = path
        stage = 'clip'
        window.clear_loop()
        job = ClipJob('https://www.youtube.com/watch?v=M7lc1UVf-VE', 2, 4, str(output), True)
        window._diagnostic_job = job
        job.events.finished.connect(clipped)
        QThreadPool.globalInstance().start(job)

    def tick():
        nonlocal stage, began
        try:
            if time.monotonic()-began > 90:
                finish('Feature check timed out: '+stage)
                return
            if stage == 'web':
                state = window.youtube.state
                if state.get('error'):
                    finish(str(state))
                elif state.get('time', 0) > 1:
                    report['youtube'] = dict(state)
                    report['blocked_requests'] = window.youtube.blocker.blocked
                    window.choose_tool('pen')
                    window.canvas.begin(QPointF(400, 400))
                    window.canvas.move(QPointF(1400, 700))
                    window.canvas.drawing = False
                    window.refresh_ink()
                    window.capture_image().save(str(output/'youtube-ink.png'))
                    window.apply_loop(5000, 7000)
                    window.recorder.finished.connect(recorded)
                    window.recorder.start(str(output), system_audio=False, microphone=False)
                    stage = 'recording'
                    began = time.monotonic()
            elif stage == 'recording' and time.monotonic()-began > 4:
                report['loop_position_ms'] = window.current_position()
                if not 4500 <= report['loop_position_ms'] < 8000:
                    raise RuntimeError('YouTube loop position outside selected segment')
                import pyaudiowpatch
                report['audio_module_loaded'] = bool(pyaudiowpatch.PyAudio)
                window.recorder.stop()
                stage = 'encoding'
        except Exception as exc:
            finish(repr(exc))

    window.load_youtube('M7lc1UVf-VE')
    timer.timeout.connect(tick)
    timer.start(200)
