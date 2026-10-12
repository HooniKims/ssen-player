# Keep Qt/FFmpeg DLLs dynamically linked. Onedir avoids unpacking on every launch.
from pathlib import Path
import PySide6
import yt_dlp
from PyInstaller.utils.hooks import collect_data_files
root = Path(SPECPATH)
import runpy
import shutil
runpy.run_path(str(root/'scripts/prepare_legal.py'))['prepare']()
runpy.run_path(str(root/'scripts/prepare_auth.py'), run_name='__main__')
qt = Path(PySide6.__file__).parent
codec_dir = root/'vendor/ffmpeg'
ffmpeg = [(str(p), 'PySide6') for p in codec_dir.glob('*.dll')]
assert len(ffmpeg) == 5, 'Run scripts/fetch_codecs.py first'
a = Analysis(['main.py'], pathex=[str(root)], binaries=ffmpeg,
    datas=[('LICENSE', '.'), ('assets', 'assets'), ('build/update.json', 'build'), ('build/codecs.json', 'build'), ('docs/THIRD-PARTY-NOTICES.txt', 'docs')]+collect_data_files('yt_dlp_ejs'),
    hiddenimports=['adblock','pyaudiowpatch','PySide6.QtSvg'], hookspath=[str(Path(yt_dlp.__file__).parent/'__pyinstaller')], runtime_hooks=[],
    excludes=['tkinter'],
    noarchive=False)
# Qt's hook may discover its smaller stock FFmpeg DLLs. Replace every matching
# destination explicitly so the released app also includes the AV1 SW decoder.
codec_names = {Path(source).name for source, _ in ffmpeg}
a.binaries = [(dest, str(codec_dir/Path(dest).name) if Path(dest).name in codec_names else source, kind)
              for dest, source, kind in a.binaries]
# The display wordmark is outlined SVG; do not ship its source font.
a.datas = [(dest, source, kind) for dest, source, kind in a.datas if not dest.endswith('Ghanachocolate.ttf')]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='SsenPlayer', debug=False,
    bootloader_ignore_signals=False, strip=False, upx=False, console=False, icon='assets/icon.ico', version='build/version-info.txt')
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='SsenPlayer')
shutil.copyfile(root/'build/LICENSE.txt', Path(coll.name)/'LICENSE.txt')
assert (Path(coll.name)/'LICENSE.txt').read_text('utf-16') == (root/'LICENSE').read_text('utf-8')
