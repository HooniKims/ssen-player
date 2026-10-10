"""Stable Windows taskbar identity, shared with installer shortcuts."""
import ctypes
import sys

APP_USER_MODEL_ID = 'HooniKim.SsenPlayer'


def set_taskbar_identity():
    if sys.platform != 'win32':
        return
    set_id = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID
    set_id.argtypes = [ctypes.c_wchar_p]
    set_id.restype = ctypes.c_long
    result = set_id(APP_USER_MODEL_ID)
    if result < 0:
        raise OSError(f'Windows taskbar identity failed: 0x{result & 0xffffffff:08x}')
