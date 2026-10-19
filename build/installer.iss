#define AppVersion "1.2.1"
[Setup]
AppId={{1459D467-38B3-4749-8E5B-30F20D09F772}
AppName=쎈Player
AppVersion={#AppVersion}
VersionInfoCopyright=Copyright 2026 상명초 김승현, 등촌중 김형훈
LicenseFile=LICENSE.txt
DisableWelcomePage=no
AppPublisher=HooniKim
DefaultDirName={localappdata}\Programs\SsenPlayer
DefaultGroupName=쎈Player
PrivilegesRequired=lowest
OutputDir=..\artifacts
OutputBaseFilename=SsenPlayer-Setup-{#AppVersion}
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\SsenPlayer.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=yes
ChangesAssociations=yes
[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
[Files]
Source: "..\dist\SsenPlayer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{autoprograms}\쎈Player"; Filename: "{app}\SsenPlayer.exe"; IconFilename: "{app}\SsenPlayer.exe"; AppUserModelID: "HooniKim.SsenPlayer"
Name: "{autodesktop}\쎈Player"; Filename: "{app}\SsenPlayer.exe"; IconFilename: "{app}\SsenPlayer.exe"; AppUserModelID: "HooniKim.SsenPlayer"; Tasks: desktopicon
[Tasks]
Name: desktopicon; Description: "바탕 화면에 바로가기 만들기"; Flags: unchecked
[Run]
Filename: "{app}\SsenPlayer.exe"; Description: "쎈Player 실행"; Flags: nowait postinstall skipifsilent

#include "associations.iss"
