#define AppVersion "0.2.0"
[Setup]
AppId={{1459D467-38B3-4749-8E5B-30F20D09F772}
AppName=쎈player
AppVersion={#AppVersion}
AppPublisher=HooniKim
DefaultDirName={localappdata}\Programs\SsenPlayer
DefaultGroupName=쎈player
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
[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
[Files]
Source: "..\dist\SsenPlayer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{autoprograms}\쎈player"; Filename: "{app}\SsenPlayer.exe"
Name: "{autodesktop}\쎈player"; Filename: "{app}\SsenPlayer.exe"; Tasks: desktopicon
[Tasks]
Name: desktopicon; Description: "바탕 화면에 바로가기 만들기"; Flags: unchecked
[Run]
Filename: "{app}\SsenPlayer.exe"; Description: "쎈player 실행"; Flags: nowait postinstall skipifsilent
