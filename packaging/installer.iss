; Inno Setup : installateur Windows de e-NABLE CustomLab (construit par .github/workflows/build.yml, après PyInstaller -> dist\CustomLab\)
[Setup]
AppName=e-NABLE CustomLab
AppVersion=0.9.0-test
AppPublisher=e-NABLE CustomLab
DefaultDirName={autopf}\e-NABLE CustomLab
DefaultGroupName=e-NABLE CustomLab
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=e-NABLE_CustomLab_Setup
SetupIconFile=CustomLab.ico
UninstallDisplayIcon={app}\CustomLab.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Files]
Source: "..\dist\CustomLab\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\e-NABLE CustomLab"; Filename: "{app}\CustomLab.exe"
Name: "{autodesktop}\e-NABLE CustomLab"; Filename: "{app}\CustomLab.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le Bureau"; Flags: unchecked

[Run]
Filename: "{app}\CustomLab.exe"; Description: "Lancer e-NABLE CustomLab"; Flags: nowait postinstall skipifsilent
