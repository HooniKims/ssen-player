import os
import sys
import json
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
if '--file' not in sys.argv:
    import subprocess
    results = []
    for path in sorted((ROOT/'artifacts/test-media').glob('*')):
        if path.suffix not in ('.mov','.mp4','.mkv','.avi','.webm'): continue
        output = ROOT/'artifacts/qa'/f'{path.stem}-codec.json'
        with (ROOT/'artifacts/qa'/f'{path.stem}-codec.log').open('w') as log:
            try:
                subprocess.run([sys.executable,__file__,'--file',str(path)],stdout=log,stderr=log,timeout=25,check=True)
                result = json.loads(output.read_text('utf-8'))[0]
            except Exception as error:
                result = dict(file=path.name, passed=False, error=str(error))
        results.append(result)
        print(json.dumps(result), flush=True)
    (ROOT/'artifacts/qa/codecs.json').write_text(json.dumps(results,indent=2),'utf-8')
    raise SystemExit(0 if results and all(r.get('passed',True) for r in results) else 1)
os.environ['QT_MEDIA_BACKEND'] = 'ffmpeg'
from app.runtime import prepare
prepare()
from PySide6.QtWidgets import QApplication
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QVideoSink, QAudioBufferOutput
from PySide6.QtCore import QUrl, Qt
from PySide6.QtTest import QTest
app = QApplication([])
results = []
for path in [Path(sys.argv[sys.argv.index('--file')+1])]:
    if path.suffix not in ('.mov', '.mp4', '.mkv', '.avi', '.webm'): continue
    player = QMediaPlayer()
    audio = QAudioOutput()
    audio.setMuted(True)
    sink = QVideoSink()
    player.setAudioOutput(audio)
    player.setVideoSink(sink)
    decoded_audio = []
    audio_buffer = QAudioBufferOutput(player)
    audio_buffer.audioBufferReceived.connect(lambda buf:decoded_audio.append(buf.frameCount()) if buf.isValid() else None, Qt.QueuedConnection)
    player.setAudioBufferOutput(audio_buffer)
    frames = []
    sink.videoFrameChanged.connect(lambda frame: frames.append(frame.startTime()) if frame.isValid() else None, Qt.QueuedConnection)
    player.setSource(QUrl.fromLocalFile(str(path)))
    player.play()
    for _ in range(100):
        QTest.qWait(50)
        if sink.videoFrame().isValid() or player.error() != QMediaPlayer.NoError: break
    frame = sink.videoFrame()
    image = frame.toImage()
    result = dict(file=path.name, decoded=not image.isNull(), width=image.width(), height=image.height(), error=player.errorString())
    if result['decoded']:
        QTest.qWait(650)
        result['advancing_frames'] = len(set(frames)) >= 3 and player.position() > 200
        result['audio_decode'] = bool(sum(decoded_audio)) if player.hasAudio() else 'no audio track'
        player.pause()
        QTest.qWait(100)
        position = player.position()
        QTest.qWait(150)
        result['pause'] = player.position() == position
        target = player.duration()//2
        frames.clear()
        player.setPosition(target)
        limit = time.monotonic()+5
        while not frames and time.monotonic() < limit: QTest.qWait(50)
        result['seek'] = bool(frames) and abs(frames[-1]/1000-target) < 500
        player.play()
        QTest.qWait(300)
        result['resume'] = player.position() > target+100
    results.append(result)
    if not image.isNull(): image.save(str(ROOT/'artifacts/qa'/f'{path.stem}-frame.png'))
    player.stop()
print(json.dumps(results, indent=2))
(ROOT/'artifacts/qa'/f'{path.stem}-codec.json').write_text(json.dumps(results, indent=2), 'utf-8')
assert results, 'No media fixtures found'
assert all(all(r.get(k) for k in ('decoded','advancing_frames','audio_decode','pause','seek','resume')) for r in results), results
