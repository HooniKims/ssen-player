# Keep Qt/FFmpeg DLLs dynamically linked. Onedir avoids unpacking on every launch.
from pathlib import Path
import PySide6
import yt_dlp
from PyInstaller.utils.hooks import collect_data_files
root = Path(SPECPATH)
qt = Path(PySide6.__file__).parent
ffmpeg = [(str(p), 'PySide6') for mask in ('avcodec-*.dll','avformat-*.dll','avutil-*.dll','swresample-*.dll','swscale-*.dll') for p in qt.glob(mask)]
a = Analysis(['main.py'], pathex=[str(root)], binaries=ffmpeg,
    datas=[('assets', 'assets'), ('build/update.json', 'build'), ('docs/THIRD-PARTY-NOTICES.txt', 'docs')]+collect_data_files('yt_dlp_ejs'),
    hiddenimports=['adblock','pyaudiowpatch'], hookspath=[str(Path(yt_dlp.__file__).parent/'__pyinstaller')], runtime_hooks=[],
    excludes=['tkinter'],
    noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='SsenPlayer', debug=False,
    bootloader_ignore_signals=False, strip=False, upx=False, console=False, icon='assets/icon.ico')
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='SsenPlayer')
