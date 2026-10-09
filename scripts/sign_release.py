"""Sign a release manifest with an external Ed25519 private PEM key."""
import argparse
import base64
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from app.updater import canonical, https_url, version_tuple

p = argparse.ArgumentParser()
p.add_argument('--key', required=True)
p.add_argument('--installer', required=True)
p.add_argument('--url', required=True)
p.add_argument('--version', required=True)
p.add_argument('--output', default='artifacts/update.json')
args = p.parse_args()
version_tuple(args.version)
https_url(args.url)
binary = Path(args.installer).read_bytes()
payload = dict(version=args.version, url=args.url, size=len(binary), sha256=hashlib.sha256(binary).hexdigest())
key = load_pem_private_key(Path(args.key).read_bytes(), password=None)
document = dict(payload=payload, signature=base64.b64encode(key.sign(canonical(payload))).decode())
Path(args.output).parent.mkdir(parents=True, exist_ok=True)
Path(args.output).write_text(json.dumps(document, ensure_ascii=False, indent=2), 'utf-8')
print(args.output)
