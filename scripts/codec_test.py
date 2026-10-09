import os
import sys
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ['QT_MEDIA_BACKEND'] = 'ffmpeg'
from PySide6.QtWidgets import QApplication
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QVideoSink
from PySide6.QtCore import QUrl
from PySide6.QtTest import QTest
app = QApplication([])
results = []
for path in sorted((ROOT/'artifacts/test-media').glob('*')):
    if path.suffix not in ('.mov', '.mp4', '.mkv', '.avi', '.webm'): continue
    player = QMediaPlayer()
    audio = QAudioOutput()
    audio.setMuted(True)
    sink = QVideoSink()
    player.setAudioOutput(audio)
    player.setVideoSink(sink)
    player.setSource(QUrl.fromLocalFile(str(path)))
    player.play()
    for _ in range(100):
        QTest.qWait(50)
        if sink.videoFrame().isValid() or player.error() != QMediaPlayer.NoError: break
    frame = sink.videoFrame()
    image = frame.toImage()
    result = dict(file=path.name, decoded=not image.isNull(), width=image.width(), height=image.height(), error=player.errorString())
    results.append(result)
    if not image.isNull(): image.save(str(ROOT/'artifacts/qa'/f'{path.stem}-frame.png'))
    player.stop()
print(json.dumps(results, indent=2))
(ROOT/'artifacts/qa/codecs.json').write_text(json.dumps(results, indent=2), 'utf-8')
assert all(r['decoded'] for r in results)
