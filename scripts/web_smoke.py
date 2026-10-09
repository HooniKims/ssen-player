import os
import sys
import time
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt,QSettings,QPointF
from PySide6.QtTest import QTest
from app.player import Player
from app.style import STYLE
QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
app=QApplication([])
app.setStyleSheet(STYLE)
out=ROOT/'artifacts/qa/web'
out.mkdir(parents=True,exist_ok=True)
window=Player(QSettings(str(out/'settings.ini'),QSettings.IniFormat))
window.show()
window.load_youtube('M7lc1UVf-VE')
deadline=time.monotonic()+45
while time.monotonic()<deadline:
    QTest.qWait(200)
    if window.youtube.state.get('time',0)>1 or window.youtube.state.get('error'): break
window.choose_tool('pen')
window.canvas.begin(QPointF(400,400))
window.canvas.move(QPointF(1400,700))
window.canvas.drawing=False
window.refresh_ink()
QTest.qWait(200)
window.grab().save(str(out/'youtube.png'))
report=dict(state=window.youtube.state,blocked=window.youtube.blocker.blocked,status=window.status.text())
if window.youtube.state.get('time',0)>1 and not window.youtube.state.get('error'):
    window.apply_loop(5000,7000)
    samples=[]
    for i in range(24):
        QTest.qWait(250)
        time.sleep(.003)
        if i>5: samples.append(window.current_position())
    assert samples and min(samples)>=4500 and max(samples)<7800,samples
    report['youtube_loop']=True
    recorded=[]
    window.recorder.finished.connect(lambda path,error:recorded.append((path,error)))
    window.recorder.start(str(out),system_audio=False,microphone=False)
    for i in range(30):
        window.canvas.begin(QPointF(600+i*8,600))
        window.canvas.move(QPointF(600+i*8,700))
        window.canvas.drawing=False
        window.refresh_ink()
        QTest.qWait(100)
        time.sleep(.005)
    window.recorder.stop()
    for i in range(200):
        QTest.qWait(50)
        time.sleep(.005)
        if recorded: break
    assert recorded and not recorded[0][1],recorded
    report['youtube_recording']=recorded[0][0]
    window.clear_loop()
(out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
if window.youtube.state.get('ready'): window.capture_image().save(str(out/'youtube-ink.png'))
print(json.dumps(report,ensure_ascii=False,indent=2))
window.close()
app.processEvents()
