"""Install and uninstall only an isolated build inside this workspace."""
import json
import subprocess
import winreg
from pathlib import Path

root = Path(__file__).resolve().parent.parent
target = (root/'.tools/install-smoke').resolve()
if root not in target.parents or target.name != 'install-smoke':
    raise RuntimeError('Unsafe installation test directory')
try:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Uninstall\{1459D467-38B3-4749-8E5B-30F20D09F772}_is1') as key:
        installed = Path(winreg.QueryValueEx(key, 'InstallLocation')[0]).resolve()
        if installed != target:
            raise RuntimeError('An existing user installation must not be replaced by this test: '+str(installed))
except FileNotFoundError:
    pass
installer = root/'artifacts/SsenPlayer-Setup-0.2.1.exe'
output = root/'artifacts/qa/installed-0.2.1'
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
checked = []
for media in sorted((root/'artifacts/test-media').glob('*')):
    if media.suffix not in ('.mov','.mp4','.mkv','.avi','.webm'):
        continue
    destination = output/media.stem
    subprocess.run([str(exe),str(media),'--smoke-test-output',str(destination)],check=True,timeout=30)
    sample = json.loads((destination/'packaged.json').read_text('utf-8'))
    assert sample['decoded'] and sample['capture_with_ink'], media.name
    checked.append(media.name)
report['installed_media_samples'] = checked
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
