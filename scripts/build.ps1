param([string]$Iscc = '.tools/InnoSetup/ISCC.exe')
$ErrorActionPreference = 'Stop'
& .venv/Scripts/python.exe -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
& .venv/Scripts/python.exe -m PyInstaller --noconfirm --workpath build/output SsenPlayer.spec
if ($LASTEXITCODE -ne 0) { throw 'Packaging failed' }
if (-not (Test-Path -LiteralPath $Iscc)) { throw 'Install Inno Setup and pass -Iscc <ISCC.exe path>' }
& $Iscc build/installer.iss
if ($LASTEXITCODE -ne 0) { throw 'Installer build failed' }
