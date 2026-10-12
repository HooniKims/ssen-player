from .media_tools import resource
from .theme import COLORS, BODY, HEADING, DISPLAY

STYLE = """
QMainWindow, QDialog { background:$canvas; color:$ink; }
QWidget { font-family:"@body","Malgun Gothic"; font-size:16px; font-weight:400; color:$ink; }
QFrame#header { background:$surface; border-bottom:1px solid $line; }
QFrame#footer, QFrame#tools { background:$surface; border:0; border-radius:16px; }
QFrame#toolOptions { background:$surface; }
QLabel#muted { color:$muted; font-size:15px; }
QLabel#section { font-family:"@heading"; font-size:19px; color:$strong; padding:6px 0; }
QLabel#dialogTitle { font-family:"@heading"; font-size:21px; color:$strong; padding-bottom:12px; }
QLabel#status { color:$muted; font-size:15px; padding:2px 8px; }
QLabel#toast { background:$toast; color:white; border-radius:10px; padding:12px 20px; font-family:"@heading"; font-size:16px; }
QPushButton { font-family:"@display"; font-size:15px; background:$surface; border:1px solid $button_line; border-radius:8px; padding:0 12px; min-height:42px; }
QPushButton:hover { background:$canvas; border-color:$muted; }
QPushButton:pressed { background:$mint; }
QPushButton:checked { background:$mint; border-color:$primary; color:$brand; }
QPushButton:focus { border:2px solid $primary; }
QPushButton:disabled { color:$info; background:$canvas; }
QPushButton#primary { background:$primary; color:white; border-color:$primary; }
QPushButton#primary:hover { background:$brand; }
QPushButton#primary:pressed { background:$pressed; }
QPushButton#small { min-height:34px; font-size:14px; padding:0 10px; }
QPushButton#tool, QPushButton#color { padding:0 6px; }
QScrollArea { border:0; background:transparent; }
QScrollBar:vertical { width:10px; background:$canvas; border:0; }
QScrollBar::handle:vertical { background:$button_line; border-radius:5px; min-height:24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
QSlider::groove:horizontal { height:6px; background:$line; border-radius:3px; }
QSlider::sub-page:horizontal { background:$primary; border-radius:3px; }
QSlider::handle:horizontal { width:16px; margin:-6px 0; background:$primary; border:2px solid white; border-radius:9px; }
QComboBox, QDoubleSpinBox { background:$surface; padding:0 10px; border:1px solid $button_line; border-radius:8px; min-height:42px; }
QComboBox::drop-down { border:0; width:20px; }
QComboBox QAbstractItemView { background:$surface; selection-background-color:$mint; selection-color:$brand; padding:6px; }
QListWidget { background:$surface; border:0; border-radius:16px; padding:8px; }
QListWidget::item { padding:12px 8px; border-bottom:1px solid $line; }
QListWidget::item:selected { background:$mint; color:$brand; }
QLabel#countdown { font-family:"@display"; font-size:96px; color:white; background:$toast; border-radius:16px; }
QToolTip { background:$toast; color:white; border:0; padding:8px; }
QCheckBox { font-family:"@display"; font-size:15px; spacing:10px; padding:6px 0; }
QCheckBox::indicator { width:20px; height:20px; border:1px solid $button_line; border-radius:4px; background:$surface; }
QCheckBox::indicator:checked { background:$primary; border-color:$primary; image:url("@check"); }
QLineEdit { background:$surface; padding:10px 12px; border:1px solid $button_line; border-radius:8px; }
QPlainTextEdit { background:$surface; padding:12px; border:1px solid $button_line; border-radius:8px; font-size:15px; }
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus { border:2px solid $primary; }
"""
for key, value in COLORS.items():
    STYLE = STYLE.replace('$' + key, value)
STYLE = STYLE.replace('@body', BODY).replace('@heading', HEADING).replace('@display', DISPLAY)
STYLE = STYLE.replace('@check', resource('assets/icons/white/check.svg').as_posix())
STYLE += 'QComboBox::down-arrow { image:url("'+resource('assets/icons/green/caret-down.svg').as_posix()+'"); width:13px; height:13px; }'

STYLE += "\nQLabel#authNotice { background: #FDF1E2; color: #7D490E; border-radius: 8px; padding: 8px 14px; }"
