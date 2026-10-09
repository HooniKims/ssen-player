"""Install and uninstall only an isolated build inside this workspace."""
import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parent.parent
target = (root/'.tools/install-smoke').resolve()
if root not in target.parents or target.name != 'install-smoke':
    raise RuntimeError('Unsafe installation test directory')
installer = root/'artifacts/SsenPlayer-Setup-0.2.0.exe'
output = root/'artifacts/qa/installed'
output.mkdir(parents=True, exist_ok=True)
startup = subprocess.STARTUPINFO()
startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startup.wShowWindow = 0
subprocess.run([str(installer), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/NOICONS',
                '/DIR='+str(target), '/LOG='+str(output/'install.log')],
               check=True, timeout=180, startupinfo=startup)
exe = target/'SsenPlayer.exe'
assert exe.is_file()
subprocess.run([str(exe), str(root/'artifacts/test-media/classroom.mov'),
                '--smoke-test-output', str(output)], check=True, timeout=30)
report = json.loads((output/'packaged.json').read_text('utf-8'))
assert report['decoded'] and report['capture_with_ink']
subprocess.run([str(exe), '--feature-test-output', str(output/'features')], check=True, timeout=150)
features = json.loads((output/'features/features.json').read_text('utf-8'))
assert not features['error'] and features['recording'] and features['clip']
assert features['audio_module_loaded']
report['youtube_recording_export'] = True
uninstaller = target/'unins000.exe'
assert uninstaller.is_file() and target in uninstaller.resolve().parents
subprocess.run([str(uninstaller), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART'],
               check=True, timeout=60, startupinfo=startup)
assert not exe.exists(), 'Uninstaller did not remove the isolated installation'
report.update(installed=True, uninstalled=True)
(output/'result.json').write_text(json.dumps(report, indent=2), 'utf-8')
print(json.dumps(report, indent=2))
