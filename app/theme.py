"""SEN series design guide v1.0, adapted to native Qt widgets."""
from PySide6.QtGui import QFontDatabase, QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect
from .media_tools import resource

COLORS = dict(canvas='#F2F0EB', surface='#FFFFFF', brand='#006241', primary='#00754A',
              pressed='#005A39', mint='#D4E9E2', ink='#1F1F1F', strong='#111111',
              muted='#555555', line='#E3E0D8', button_line='#D9D5CC', toast='#1E3932',
              danger='#C23B22', warn='#B25E09', ok='#00754A', info='#6B6B6B')
BODY = 'Cafe24 PRO Slim Air'
HEADING = 'Cafe24 PRO Slim Max'
DISPLAY = 'Hakgyoansim Jayeon R'
_loaded = False

def load_fonts():
    global _loaded
    if _loaded:
        return
    for name in ('Cafe24PROSlimAir.otf', 'Cafe24PROSlimMax.otf', 'Hakgyoansim_JayeonR.ttf'):
        if QFontDatabase.addApplicationFont(str(resource('assets/fonts/' + name))) < 0:
            raise RuntimeError('Bundled font could not be loaded: ' + name)
    _loaded = True

def panel_shadow(widget):
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(18)
    effect.setOffset(0, 3)
    effect.setColor(QColor(31, 31, 31, 18))
    widget.setGraphicsEffect(effect)
