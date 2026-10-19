"""Subprocess fixture for real Qt local IPC (not included in the app bundle)."""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QCoreApplication, QTimer
from app.single_instance import SingleInstance

app = QCoreApplication([])
root, mode, *paths = sys.argv[1:]
root = Path(root)
instance = SingleInstance(directory=root)
instance.files_received.connect(lambda paths: (root/'received.jsonl').open('a', encoding='utf-8').write(json.dumps(paths) + '\n'))
primary = instance.start(paths, timeout=3)
if primary:
    (root/'owner').write_text(str(__import__('os').getpid()))
    if mode == 'delayed': time.sleep(0.8)
    app.aboutToQuit.connect(instance.close)
    timer = QTimer()
    timer.timeout.connect(lambda: app.quit() if (root/'stop').exists() else None)
    timer.start(25)
    QTimer.singleShot(15000, app.quit)
    app.exec()
print('owner' if primary else 'forwarded')
