"""Create installer terms and executable version resources from source files."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app import VERSION

COPYRIGHT = 'Copyright 2026 상명초 김승현, 등촌중 김형훈'


def prepare():
    text = (ROOT/'LICENSE').read_text('utf-8')
    (ROOT/'build/LICENSE.txt').write_bytes(text.replace('\r\n', '\n').replace('\n', '\r\n').encode('utf-16'))
    version = tuple(map(int, VERSION.split('.'))) + (0,)
    strings = {'CompanyName': 'HooniKim', 'FileDescription': '쎈player', 'FileVersion': VERSION,
               'InternalName': 'SsenPlayer', 'LegalCopyright': COPYRIGHT,
               'OriginalFilename': 'SsenPlayer.exe', 'ProductName': '쎈player', 'ProductVersion': VERSION}
    entries = ',\n'.join(f'StringStruct({k!r}, {v!r})' for k, v in strings.items())
    data = f"VSVersionInfo(ffi=FixedFileInfo(filevers={version!r}, prodvers={version!r}, mask=0x3f, flags=0, OS=0x40004, fileType=1, subtype=0, date=(0,0)), kids=[StringFileInfo([StringTable('041204b0', [{entries}])]), VarFileInfo([VarStruct('Translation', [1042,1200])])])"
    (ROOT/'build/version-info.txt').write_text(data, 'utf-8')


if __name__ == '__main__':
    prepare()
