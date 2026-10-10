import os
import sys
import time
import json
import subprocess
import math
import array
import wave
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
os.environ['QT_MEDIA_BACKEND']='ffmpeg'
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings,QPointF
from PySide6.QtTest import QTest
from app.player import Player
from app.clips import ClipJob
from PySide6.QtCore import QThreadPool

out=ROOT/'artifacts/qa/v0.2'
out.mkdir(parents=True,exist_ok=True)
app=QApplication([])
settings=QSettings(str(out/'settings.ini'),QSettings.IniFormat)
settings.clear()
window=Player(settings)
window.show()
window.add_files([str(ROOT/'artifacts/test-media/classroom.mov')])
def wait(condition,seconds=20):
    deadline=time.monotonic()+seconds
    while not condition():
        if time.monotonic()>deadline: raise AssertionError('timeout')
        QTest.qWait(50)
wait(lambda:window.media.position()>400 and window.canvas.video.videoSink().videoFrame().isValid())
recorded=[]
window.recorder.finished.connect(lambda p,e:recorded.append((p,e)))
window.recorder.start(str(out),system_audio=False,microphone=False)
# Exercise two-track audio mixing without recording ambient system/microphone audio.
for frequency in (440,660):
    audio=window.recorder.workspace/f'synthetic-{frequency}.wav'
    samples=array.array('h',(round(3500*math.sin(2*math.pi*frequency*i/48000)) for i in range(48000*6)))
    with wave.open(str(audio),'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(48000)
        wav.writeframes(samples.tobytes())
    window.recorder.audio_files.append(audio)
QTest.qWait(900)
window.choose_tool('pen')
window.canvas.color='#ffffff'
window.canvas.pen_width=18
window.canvas.stroke_begin(QPointF(300,500))
for x in range(320,1500,20):
    window.canvas.stroke_move(QPointF(x,500))
    QTest.qWait(15)
window.canvas.stroke_end()
window.media.pause()
QTest.qWait(800)
window.recorder.stop()
wait(lambda:bool(recorded),30)
assert not recorded[0][1],recorded
recording=recorded[0][0]
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',recording]))
duration=float(probe['format']['duration'])
assert 2.4 < duration < 5,duration
assert probe['streams'][0]['codec_name']=='h264'
assert probe['streams'][0]['width']==1280
assert any(s['codec_name']=='aac' for s in probe['streams'])
subprocess.run(['ffmpeg','-v','error','-y','-ss','2.3','-i',recording,'-frames:v','1',str(out/'recorded-ink.png')],check=True)
from PIL import Image
image=Image.open(out/'recorded-ink.png').convert('RGB')
pixel=image.getpixel((600,333))
assert min(pixel)>200,pixel
window.apply_loop(1000,2000)
QTest.qWait(2700)
assert 900 <= window.media.position() <= 2100,window.media.position()
window.clear_loop()
window.show_segments()
from PySide6.QtWidgets import QLineEdit,QDoubleSpinBox,QPushButton
dialog=window.segment_dialog
spins=dialog.findChildren(QDoubleSpinBox)
spins[0].setValue(1)
spins[1].setValue(2)
next(field for field in dialog.findChildren(QLineEdit) if field.placeholderText().startswith('구간 이름')).setText('실험 장면')
next(b for b in dialog.findChildren(QPushButton) if b.text()=='구간 목록에 저장').click()
assert window.segment_data()[window.current][-1]['name']=='실험 장면'
dialog.close()
assert window.segment_dialog is None
result=[]
job=ClipJob(str(ROOT/'artifacts/test-media/classroom.mov'),2,4,out)
job.events.finished.connect(lambda p,e:result.append((p,e)))
QThreadPool.globalInstance().start(job)
wait(lambda:bool(result),30)
assert not result[0][1],result
clip=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',result[0][0]]))
assert abs(float(clip['format']['duration'])-2)<.15
assert any(s['codec_type']=='audio' for s in clip['streams'])
report=dict(recording=recording,recording_seconds=duration,moving_ink=True,paused_scene_recorded=True,
            clip=result[0][0],clip_audio=True,loop=True,saved_segments=True,two_audio_tracks_mixed=True)
(out/'recording-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
window.close()
