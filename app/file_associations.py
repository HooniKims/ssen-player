"""Register as a candidate player; Windows owns the user's default choice."""
import sys
from pathlib import Path

APP_NAME = 'SsenPlayer'
PROG_ID = 'SsenPlayer.Video'
CAPABILITIES = r'Software\HooniKim\SsenPlayer\Capabilities'
EXTENSIONS = ('.mov', '.mp4', '.mkv', '.avi', '.webm', '.m4v', '.wmv', '.flv',
              '.ts', '.mts', '.m2ts', '.mpg', '.mpeg', '.3gp')
SETTINGS_URI = 'ms-settings:defaultapps?registeredAppUser=SsenPlayer'


def registration_entries(executable):
    exe = str(executable)
    entries = [
        (rf'Software\Classes\{PROG_ID}', '', '쎈Player 동영상'),
        (rf'Software\Classes\{PROG_ID}\DefaultIcon', '', f'"{exe}",0'),
        (rf'Software\Classes\{PROG_ID}\shell\open\command', '', f'"{exe}" "%1"'),
        (CAPABILITIES, 'ApplicationName', '쎈Player'),
        (CAPABILITIES, 'ApplicationDescription', '영상 재생과 필기·캡처를 위한 수업용 플레이어'),
        (CAPABILITIES, 'ApplicationIcon', f'"{exe}",0'),
        (r'Software\RegisteredApplications', APP_NAME, CAPABILITIES),
    ]
    for ext in EXTENSIONS:
        entries.extend([
            (CAPABILITIES + r'\FileAssociations', ext, PROG_ID),
            (rf'Software\Classes\{ext}\OpenWithProgids', PROG_ID, ''),
        ])
    return entries


def register_player():
    from .auth_gate import require_authorized
    require_authorized()
    if sys.platform != 'win32' or not getattr(sys, 'frozen', False):
        raise RuntimeError('설치한 쎈Player 또는 포터블 EXE에서 기본 앱 설정을 열어 주세요.')
    import winreg
    for path, name, value in registration_entries(Path(sys.executable).resolve()):
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, path) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
    import ctypes
    ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)


def is_default_player():
    if sys.platform != 'win32':
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.mp4\UserChoice') as key:
            return winreg.QueryValueEx(key, 'ProgId')[0] == PROG_ID
    except OSError:
        return False
