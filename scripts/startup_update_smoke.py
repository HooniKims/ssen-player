"""Exercise main.main's ordinary startup path, with isolated auth/settings and no network."""
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PySide6.QtCore import QTimer, QSettings
from PySide6.QtWidgets import QApplication
from app.single_instance import SingleInstance
from app.player import Player
from subtitle_smoke import LockedAuth
import main

with tempfile.TemporaryDirectory() as temp:
    report = {}
    def create():
        window = Player(QSettings(str(Path(temp)/'settings.ini'), QSettings.IniFormat), auth_factory=LockedAuth)
        def verify():
            c = window.updates
            report.update(normal_main_start_called=c._started, first_timer_active=c.first_timer.isActive(),
                          first_interval=c.first_timer.interval(), repeat_interval=c.repeat_timer.interval(),
                          no_automatic_download=c.installer is None and c.operation is None)
            window.close()
            QApplication.instance().quit()
        QTimer.singleShot(100, verify)
        return window
    with patch('app.player.Player', side_effect=create), patch('app.single_instance.SingleInstance', side_effect=lambda parent: SingleInstance(parent, directory=Path(temp)/'instance')), patch.object(sys, 'argv', ['main.py']):
        code = main.main()
    assert code == 0 and report['normal_main_start_called'] and report['first_timer_active']
    assert report['first_interval'] == 15000 and report['repeat_interval'] == 14400000
    target = ROOT/'artifacts/qa/updates/startup.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2), 'utf-8')
    print(json.dumps(report))
