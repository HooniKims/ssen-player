from .media_tools import resource

STYLE = '''
QMainWindow, QDialog { background:#f2f0eb; color:#183c30; }
QWidget { font-family:Ghanachocolate,"Malgun Gothic"; font-size:14px; color:#183c30; }
QFrame#header, QFrame#footer { background:#f2f0eb; }
QLabel#brand { font-family:Ghanachocolate; font-size:27px; color:#006241; }
QLabel#muted { color:#576d60; font-size:12px; }
QLabel#status { font-family:"Malgun Gothic"; color:#576d60; font-size:11px; padding:4px 10px; }
QLabel#section { color:#576d60; font-size:12px; padding:5px 2px; }
QPushButton { background:#ffffff; border:1px solid #bdd4c6; border-radius:22px; padding:0 17px; min-height:42px; }
QPushButton:hover { background:#e5f1eb; border-color:#79a58d; }
QPushButton:pressed { background:#d4e9e2; }
QPushButton:checked { background:#00754a; border-color:#00754a; color:white; }
QPushButton:focus { border:2px solid #00754a; }
QPushButton:disabled { color:#9ca69e; background:#e9ece6; }
QPushButton#primary { background:#00754a; color:white; border:1px solid #00754a; }
QPushButton#primary:hover { background:#006241; }
QPushButton#color { border-radius:15px; min-width:26px; min-height:26px; padding:0; }
QPushButton#pureExit { background:#f2f0eb; border-radius:18px; }
QPushButton#iconButton { background:transparent; border:1px solid transparent; padding:0; border-radius:22px; }
QPushButton#iconButton:hover { background:#e5f1eb; }
QPushButton#iconButton:focus { border-color:#00754a; }
QPushButton#iconButton:checked { background:#00754a; }
QFrame#tools { background:#ffffff; border:1px solid #e1e5df; border-radius:22px; }
QFrame#toolOptions { background:#ffffff; }
QFrame#tools QPushButton { padding:0 10px; }
QFrame#tools QPushButton#tool { background:#f2f7f1; border:1px solid transparent; border-radius:14px; padding:0 8px; }
QFrame#tools QPushButton#tool:hover { background:#e5f1eb; }
QFrame#tools QPushButton#tool:checked { background:#00754a; color:white; }
QFrame#tools QPushButton#color { padding:0; min-width:40px; max-width:40px; min-height:40px; max-height:40px; border-radius:21px; }
QScrollBar:vertical { width:10px; background:#f2f7f1; border:0; }
QScrollBar::handle:vertical { background:#b7cabd; border-radius:5px; min-height:24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
QSlider::groove:horizontal { height:6px; background:#dce3dc; border-radius:3px; }
QSlider::sub-page:horizontal { background:#00754a; border-radius:3px; }
QSlider::handle:horizontal { width:16px; margin:-6px 0; background:#00754a; border:2px solid white; border-radius:9px; }
QComboBox, QDoubleSpinBox { background:white; padding:0 13px; border:1px solid #e1e5df; border-radius:14px; min-height:42px; }
QComboBox::drop-down { border:0; width:23px; }
QComboBox QAbstractItemView { background:white; selection-background-color:#e5f1eb; selection-color:#006241; padding:6px; }
QListWidget { background:#fff; border:0; border-radius:12px; padding:8px; }
QListWidget::item { padding:13px 6px; border-radius:9px; }
QListWidget::item:selected { background:#e5f1eb; color:#006241; }
QScrollArea { border:0; background:transparent; }
QLabel#countdown { font-family:Ghanachocolate; font-size:96px; color:white; background:rgba(17,29,25,190); border-radius:90px; }
QToolTip { background:#183c30; color:white; border:0; padding:8px; }
QCheckBox { spacing:10px; padding:9px 0; }
QCheckBox::indicator { width:22px; height:22px; }
QLineEdit { background:white; padding:10px; border:1px solid #dce3dc; border-radius:10px; }
'''
STYLE += 'QComboBox::down-arrow { image:url("'+resource('assets/icons/caret-down.svg').as_posix()+'"); width:13px; height:13px; }'
