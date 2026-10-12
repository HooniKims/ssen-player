"""Exercise player controls and failure paths against real media, not mocks."""
import json
import sys
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from PySide6.QtCore import Qt, QSettings, QPoint, QPointF, QTimer, QEvent, QSize
from PySide6.QtGui import QFontDatabase, QMouseEvent
from PySide6.QtWidgets import QApplication, QDialog, QWidget
from PySide6.QtTest import QTest
from PySide6.QtMultimedia import QMediaPlayer, QAudioBufferOutput
from scripts.qa_auth import test_player as Player
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
    QTest.mouseClick(w.seek, Qt.LeftButton, pos=QPoint(round(w.seek.width()*.75), w.seek.height()//2))
    wait(lambda:abs(w.media.position()-w.media.duration()*.75)<w.media.duration()*.05)
    report['seek_bar_tap_jumps']=True
    w.seek_to(2000)
    QTest.qWait(200)
    w.choose_tool('marker')
    w.canvas.stroke_begin(QPointF(500,400))
    w.canvas.stroke_move(QPointF(900,400))
    w.canvas.stroke_end()
    assert len(w.canvas.ink.strokes)==1 and w.canvas.ink.strokes[0].marker
    w.choose_tool('eraser')
    w.canvas.stroke_begin(QPointF(700,400))
    w.canvas.stroke_end()
    assert not w.canvas.ink.strokes
    w.undo()
    assert len(w.canvas.ink.strokes)==1
    report['marker_erase_undo']=True
    w.choose_tool('area_eraser')
    steps=len(w.canvas.ink.history)
    w.canvas.stroke_begin(QPointF(1800,1000))
    w.canvas.stroke_end()
    assert len(w.canvas.ink.history)==steps
    report['empty_eraser_tap_no_undo_step']=True
    w.colors.buttons()[1].click()
    assert w.canvas.tool=='pen' and w.tool_buttons['pen'].isChecked() and w.canvas.color=='#ff6565'
    w.choose_tool('pointer')
    w.width_combo.setCurrentIndex(2)
    assert w.canvas.tool=='pen' and w.canvas.pen_width==12
    w.choose_tool('pointer')
    report['color_or_width_selects_pen']=True
    assert w.capture_image(1280,720).size()==QSize(1280,720)
    report['capture_at_recording_size']=True
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
    w.media.setPlaybackRate(1)  # as if the speed was changed while YouTube played
    w.next_file(1)
    wait(lambda:w.media.duration()>0 and w.current==second)
    assert not w.canvas.ink.strokes
    assert w.media.playbackRate()==1.5
    w.next_file(-1)
    wait(lambda:w.current==first and w.media.position()>1500)
    assert len(w.canvas.ink.strokes)==1
    w.seek.setRange(0,1)  # as if YouTube had owned the seek bar
    w.load(first)
    wait(lambda:w.seek.maximum()==w.media.duration())
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
    w.countdown_button.click()
    QTest.qWait(300)
    assert w.media.playbackState()!=QMediaPlayer.PlayingState and w.countdown_label.text()=='5'
    w.countdown_button.click()
    QTest.qWait(1200)
    assert w.countdown_label.isHidden() and w.media.playbackState()!=QMediaPlayer.PlayingState
    began=time.monotonic()
    w.countdown_button.click()
    wait(lambda:w.countdown_label.isHidden(),7)
    assert 4.9<time.monotonic()-began<5.4
    wait(lambda:w.media.playbackState()==QMediaPlayer.PlayingState)
    report['countdown_play_at_zero']=True
    browser=QWidget()  # stands in for the YouTube view, which receives its own touches
    w.video_stack.addWidget(browser)
    w.video_stack.setCurrentWidget(browser)
    w.set_mode('pure')
    QTest.qWait(300)
    w.pure_exit.hide()
    QApplication.sendEvent(browser, QMouseEvent(QEvent.MouseButtonPress, QPointF(10,10), QPointF(10,10), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
    assert w.pure_exit.isVisible()
    w.set_mode('window')
    QTest.qWait(300)
    QApplication.sendEvent(browser, QMouseEvent(QEvent.MouseButtonPress, QPointF(10,10), QPointF(10,10), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
    assert not w.pure_exit.isVisible()
    w.video_stack.setCurrentWidget(w.canvas)
    report['pure_fullscreen_exit_from_any_surface']=True
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
