"""Exercise the real Inno [Run]/[Code] condition with a harmless executable fixture.

No player installation, shortcuts or uninstall registry entries are changed.
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
work = ROOT/'.tools/update-restart-qa'
work.mkdir(parents=True, exist_ok=True)
source = (ROOT/'build/installer.iss').read_text('utf-8')
run = source.split('[Run]\n', 1)[1].split('#include', 1)[0]
run = run.replace(r'{app}\SsenPlayer.exe', r'{sys}\whoami.exe')
run = run.replace('Flags: nowait', 'Flags: runhidden nowait')
code = source.split('[Code]\n', 1)[1]
fixture = r'''[Setup]
AppName=SsenPlayer restart condition QA
AppVersion=1.0
AppId=SsenPlayerUpdateRestartQA
DefaultDirName={src}\isolated-target
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Uninstallable=no
CreateUninstallRegKey=no
DisableDirPage=yes
DisableProgramGroupPage=yes
OutputDir=.
OutputBaseFilename=restart-fixture
[Run]
''' + run + '\n[Code]\n' + code
script = work/'restart.iss'
script.write_text(fixture, 'utf-8-sig')
with (work/'compile.log').open('w', encoding='utf-8') as output:
    subprocess.run([str(ROOT/'.tools/InnoSetup/ISCC.exe'), str(script)], stdout=output, stderr=subprocess.STDOUT, check=True)
results = {}
for restart in (False, True):
    log = work/('with-restart.log' if restart else 'without-restart.log')
    command = [str(work/'restart-fixture.exe'), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
               '/NOCLOSEAPPLICATIONS', '/NORESTARTAPPLICATIONS', '/LOG='+str(log)]
    if restart: command.append('/RESTARTPLAYER=1')
    subprocess.run(command, check=True, timeout=30)
    text = log.read_bytes().decode('utf-8-sig', errors='replace')
    count = sum('filename:' in line.lower() and line.lower().endswith('\\whoami.exe') for line in text.splitlines())
    assert count == int(restart), (restart, count)
    results['explicit_restart' if restart else 'ordinary_silent_install'] = count
results.update(real_inno_engine=True, run_code_copied_from_product=True, harmless_whoami_fixture=True,
               real_player_installed=False)
output = ROOT/'artifacts/qa/updates/installer-restart.json'
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(results, indent=2), 'utf-8')
print(json.dumps(results))
