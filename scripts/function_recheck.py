"""Exercise player controls and failure paths against real media, not mocks."""
import json
import sys
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from PySide6.QtCore import Qt, QSettings, QPointF, QTimer
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtTest import QTest
from PySide6.QtMultimedia import QMediaPlayer, QAudioBufferOutput
from app.player import Player
from app.style import STYLE

app=QApplication([])
QFontDatabase.addApplicationFont(str(ROOT/'assets/Ghanachocolate.ttf'))
app.setStyle('Fusion')
app.setStyleSheet(STYLE)
out=ROOT/'artifacts/qa/recheck'
out.mkdir(parents=True,exist_ok=True)
settings=QSettings(str(out/'settings.ini'),QSettings.IniFormat)
settings.clear()
w=Player(settings)
w.show()
report={}
def wait(check,seconds=10):
    end=time.monotonic()+seconds
    while not check():
        assert time.monotonic()<end, 'Condition timed out'
        QTest.qWait(40)
        time.sleep(.002)
try:
    w.capture()
    assert not w.jobs and '영상' in w.status.text()
    report['empty_capture_guard']=True
    audio=QAudioBufferOutput(w)
    buffers=[]
    audio.audioBufferReceived.connect(lambda b:buffers.append(b.frameCount()) if b.isValid() else None)
    w.media.setAudioBufferOutput(audio)
    first=str(ROOT/'artifacts/test-media/classroom.mov')
    second=str(ROOT/'artifacts/test-media/h264.mp4')
    w.add_files([first,second,first])
    wait(lambda:w.media.position()>600 and w.canvas.video.videoSink().videoFrame().isValid())
    assert len(w.queue)==2
    wait(lambda:sum(buffers)>0)
    report['audio_decoded']=True
    w.toggle()
    wait(lambda:w.media.playbackState()==QMediaPlayer.PausedState)
    w.seek_to(2000)
    QTest.qWait(200)
    w.jump(5000)
    assert abs(w.media.position()-7000)<100
    w.jump(-5000)
    assert abs(w.media.position()-2000)<100
    w.speed.setCurrentIndex(4)
    assert w.media.playbackRate()==1.5
    w.volume.setValue(31)
    assert abs(w.audio.volume()-.31)<.01
    w.toggle_mute()
    assert w.audio.isMuted()
    w.toggle_mute()
    assert not w.audio.isMuted()
    report['transport_speed_volume_mute']=True
    w.choose_tool('marker')
    w.canvas.begin(QPointF(500,400))
    w.canvas.move(QPointF(900,400))
    w.canvas.drawing=False
    assert len(w.canvas.ink.strokes)==1 and w.canvas.ink.strokes[0].marker
    w.choose_tool('eraser')
    w.canvas.begin(QPointF(700,400))
    w.canvas.drawing=False
    assert not w.canvas.ink.strokes
    w.undo()
    assert len(w.canvas.ink.strokes)==1
    report['marker_erase_undo']=True
    w.subtitles=[(1000,3000,'수업 자막 검증')]
    w.position(2000)
    assert w.canvas.subtitle=='수업 자막 검증'
    w.shift_subtitle(2000)
    assert w.canvas.subtitle==''
    w.shift_subtitle(-2000)
    assert w.canvas.subtitle=='수업 자막 검증'
    w.capture_image().save(str(out/'subtitle-ink.png'))
    report['external_subtitle_sync_capture']=True
    w.save_position()
    w.next_file(1)
    wait(lambda:w.media.duration()>0 and w.current==second)
    assert not w.canvas.ink.strokes
    w.next_file(-1)
    wait(lambda:w.current==first and w.media.position()>1500)
    assert len(w.canvas.ink.strokes)==1
    report['playlist_ink_isolation_resume']=True
    w.media.pause()
    w.apply_loop(1000,2000)
    QTest.qWait(2400)
    assert 900<=w.current_position()<=2200
    w.clear_loop()
    assert w.a is None and w.b is None
    report['repeat_clear']=True
    blocker=out/'not-a-folder'
    blocker.write_text('test','utf-8')
    w.capture_dir=str(blocker)
    w.capture()
    wait(lambda:not w.jobs)
    assert '저장 실패' in w.status.text()
    report['capture_io_error']=True
    QTimer.singleShot(250, lambda:[d.accept() for d in w.findChildren(QDialog)])
    w.show_settings()
    report['settings_dialog']=True
    w.resize(1050,690)
    QTest.qWait(300)
    w.grab().save(str(out/'minimum-window.png'))
    report['minimum_window_size']=[w.width(),w.height()]
    assert w.width()<=1050, report['minimum_window_size']
finally:
    (out/'functions.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
    w.close()
print(json.dumps(report,ensure_ascii=False,indent=2))
