; Inno Setup : installateur Windows de e-NableLab (construit par .github/workflows/build.yml, après PyInstaller -> dist\e-NableLab\)
[Setup]
AppName=e-NableLab
AppVersion=1.0.0-beta.2
AppPublisher=e-NABLE France
AppPublisherURL=https://e-nable.fr
AppComments=e-NableLab, By e-Nable France
WizardImageFile=wizard_large.bmp
WizardSmallImageFile=wizard_small.bmp
DefaultDirName={autopf}\e-NableLab
DefaultGroupName=e-NableLab
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=e-NableLab_Setup
SetupIconFile=e-NableLab.ico
UninstallDisplayIcon={app}\e-NableLab.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Files]
Source: "..\dist\e-NableLab\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\e-NableLab"; Filename: "{app}\e-NableLab.exe"
Name: "{autodesktop}\e-NableLab"; Filename: "{app}\e-NableLab.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le Bureau"; Flags: unchecked

[Run]
Filename: "{app}\e-NableLab.exe"; Description: "Lancer e-NableLab"; Flags: nowait postinstall skipifsilent
