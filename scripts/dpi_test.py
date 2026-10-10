"""Check scalable icons and save the real toolbar at each Windows-style scale."""
import json
import os
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from PySide6.QtCore import QSize, QSettings
from PySide6.QtGui import QIcon, QFontDatabase
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from app.controls import icon
from app.player import Player
from app.style import STYLE

app=QApplication([])
app.setStyle('Fusion')
app.setStyleSheet(STYLE)
QFontDatabase.addApplicationFont(str(ROOT/'assets/Ghanachocolate.ttf'))
out=ROOT/'artifacts/qa/dpi'
out.mkdir(parents=True,exist_ok=True)
results=[]
for scale in (1,1.25,1.5,2,3,4):
    for state in (QIcon.Off,QIcon.On):
        pix=icon('pen').pixmap(QSize(20,20),scale,QIcon.Normal,state)
        assert pix.width()==round(20*scale),(scale,pix.size(),pix.devicePixelRatio())
        assert pix.devicePixelRatio()==scale
    results.append(dict(scale=scale,pixels=round(20*scale)))
w=Player(QSettings(str(out/'settings.ini'),QSettings.IniFormat))
w.show()
QTest.qWait(350)
scale=w.devicePixelRatioF()
w.tools_scroll.grab().save(str(out/f'tools-{round(scale*100)}.png'))
w.grab().save(str(out/f'window-{round(scale*100)}.png'))
(out/f'report-{round(scale*100)}.json').write_text(json.dumps(dict(window_scale=scale,icons=results),indent=2),'utf-8')
print('DPI',scale,'all requested icon resolutions retained')
w.close()
