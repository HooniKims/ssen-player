"""Load the same pinned LGPL decoder libraries in development and EXE builds."""
import os
import sys
import ctypes
from pathlib import Path

_libraries = []
_directory = None

def prepare():
    global _directory
    if _libraries or sys.platform != 'win32': return
    # Qt 6.10 can select an unusable AV1 hardware decoder without retrying SW.
    # Use the bundled dav1d/software decoders deterministically across boards.
    os.environ.setdefault('QT_FFMPEG_DECODING_HW_DEVICE_TYPES', ',')
    folder = (Path(sys._MEIPASS)/'PySide6' if getattr(sys,'frozen',False)
              else Path(__file__).resolve().parent.parent/'vendor/ffmpeg')
    if not (folder/'avcodec-61.dll').is_file():
        raise RuntimeError('Bundled codecs missing. Run scripts/fetch_codecs.py before starting or building.')
    _directory = os.add_dll_directory(str(folder))
    for name in ('avutil-59.dll','swresample-5.dll','swscale-8.dll','avcodec-61.dll','avformat-61.dll'):
        _libraries.append(ctypes.WinDLL(str(folder/name)))
