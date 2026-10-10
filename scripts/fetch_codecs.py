"""Fetch the pinned LGPL build and verify its hash; no system installation."""
import hashlib
import json
import zipfile
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent
lock = json.loads((ROOT/'build/codecs.json').read_text('utf-8'))
archive = ROOT/'.tools/ffmpeg-lgpl-7.1.zip'
archive.parent.mkdir(parents=True,exist_ok=True)
def valid():
    return archive.exists() and hashlib.sha256(archive.read_bytes()).hexdigest()==lock['sha256']
if not valid():
    with urlopen(lock['url'], timeout=60) as response, archive.open('wb') as output:
        while chunk := response.read(1024*1024): output.write(chunk)
if not valid(): raise RuntimeError('Codec download SHA-256 mismatch')
destination = ROOT/'vendor/ffmpeg'
destination.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(archive) as bundle:
    for name in lock['libraries']:
        entry = next(n for n in bundle.namelist() if n.endswith('/bin/'+name))
        (destination/name).write_bytes(bundle.read(entry))
print('Verified LGPL codecs with dav1d:', lock['version'])
