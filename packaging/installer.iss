; Inno Setup : installateur Windows de e-NableLab (construit par .github/workflows/build.yml, après PyInstaller -> dist\e-NableLab\)
[Setup]
; AppId must NEVER change: it is how Windows recognises an installed copy. It keeps the value Inno Setup used implicitly when the app
; was called "e-NABLE CustomLab" (AppId defaults to AppName), so this installer UPDATES those copies instead of adding a second app.
AppId=e-NABLE CustomLab
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

[InstallDelete]
; leftovers of the versions named "e-NABLE CustomLab": old program and shortcuts would still start the old version
Type: files; Name: "{app}\CustomLab.exe"
Type: files; Name: "{group}\e-NABLE CustomLab.lnk"
Type: files; Name: "{autodesktop}\e-NABLE CustomLab.lnk"

[Icons]
Name: "{group}\e-NableLab"; Filename: "{app}\e-NableLab.exe"
Name: "{autodesktop}\e-NableLab"; Filename: "{app}\e-NableLab.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le Bureau"; Flags: unchecked

[Run]
Filename: "{app}\e-NableLab.exe"; Description: "Lancer e-NableLab"; Flags: nowait postinstall skipifsilent
