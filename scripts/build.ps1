param([string]$Iscc = '.tools/InnoSetup/ISCC.exe')
$ErrorActionPreference = 'Stop'
$env:SSEN_APP_ID='player'
& node --test tests/auth-kit/*.test.cjs
if ($LASTEXITCODE -ne 0) { throw 'Auth kit tests failed' }
& .venv/Scripts/python.exe -X utf8 scripts/auth_crypto_test.py
if ($LASTEXITCODE -ne 0) { throw 'Browser crypto vectors failed' }
& .venv/Scripts/python.exe scripts/render_associations.py
if ($LASTEXITCODE -ne 0) { throw 'File association generation failed' }
& .venv/Scripts/python.exe scripts/fetch_codecs.py
if ($LASTEXITCODE -ne 0) { throw 'Codec download or verification failed' }
& .venv/Scripts/python.exe -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
& .venv/Scripts/python.exe -m PyInstaller --noconfirm --workpath build/output SsenPlayer.spec
if ($LASTEXITCODE -ne 0) { throw 'Packaging failed' }
if (-not (Test-Path -LiteralPath $Iscc)) { throw 'Install Inno Setup and pass -Iscc <ISCC.exe path>' }
& $Iscc build/installer.iss
if ($LASTEXITCODE -ne 0) { throw 'Installer build failed' }
