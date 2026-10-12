"""Verify a built bundle without printing its private provenance values."""
import argparse
import json
import marshal
import re
from pathlib import Path
import pefile
from PyInstaller.archive.readers import CArchiveReader

ROOT = Path(__file__).resolve().parent.parent
p = argparse.ArgumentParser()
p.add_argument('--bundle', default=str(ROOT/'dist/SsenPlayer'))
p.add_argument('--exports', nargs='*', default=[str(ROOT/'artifacts/qa')])
args = p.parse_args()
bundle = Path(args.bundle)
terms = (ROOT/'LICENSE').read_text('utf-8')
assert (bundle/'LICENSE.txt').read_text('utf-16') == terms
assert (bundle/'_internal/LICENSE').read_text('utf-8') == terms
assert '이용약관' in terms and '김승현' in terms and '{' not in terms
tokens = re.findall(r'\| ([0-9a-f]{12}) \|', (ROOT/'docs/provenance.md').read_text('utf-8'))
assert len(set(tokens)) == 6
archive = CArchiveReader(str(bundle/'SsenPlayer.exe'))
pyz = archive.open_embedded_archive('PYZ.pyz')
code = archive.extract('main')
for module in ('app.legal', 'app.diagnostics'):
    code += marshal.dumps(pyz.extract(module))
code += (bundle/'_internal/assets/web/player.html').read_bytes()
assert all(token.encode() in code for token in tokens), 'A provenance location was not packaged'
assert not list(bundle.rglob('provenance.md'))
assert not list(bundle.rglob('*표식-적용.md'))
with pefile.PE(str(bundle/'SsenPlayer.exe')) as pe:
    strings = {}
    for group in pe.FileInfo:
        for entry in group:
            for table in getattr(entry, 'StringTable', []):
                strings.update(table.entries)
    assert strings[b'LegalCopyright'].decode('utf-8') == 'Copyright 2026 상명초 김승현, 등촌중 김형훈'
count = 0
for folder in args.exports:
    for file in Path(folder).rglob('*'):
        if file.suffix.lower() not in ('.png', '.mp4', '.srt', '.vtt'):
            continue
        data = file.read_bytes()
        assert not any(token.encode() in data or token.encode('utf-16le') in data for token in tokens), 'A user output contains a provenance value'
        count += 1
assert count > 0, 'No user output was checked'
print(json.dumps({'license_matches': True, 'exe_copyright': True,
                  'provenance_locations': 6, 'private_documents_excluded': True,
                  'clean_user_outputs': count}, indent=2))
