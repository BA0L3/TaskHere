#define AppName "TasksHere"
#define AppVersion "1.0.1"
#define AppPublisher "BA0L3"
#define DistDir "build\main_gui.dist"

[Setup]
AppId={{8979203E-BB54-4DE0-A902-167ADA603139}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
OutputDir=build\installer
OutputBaseFilename=TasksHere-Setup-{#AppVersion}
SetupIconFile=Datas\TaskHere.ico
UninstallDisplayIcon={app}\Datas\TaskHere.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; \
    GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "{#DistDir}\*"; DestDir: "{app}"; \
    Excludes: "Datas\Tasks.json,Datas\settings.json,Datas\logs\*"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\TasksHere"; Filename: "{app}\main_gui.exe"; \
    WorkingDir: "{app}"; IconFilename: "{app}\Datas\TaskHere.ico"
Name: "{autodesktop}\TasksHere"; Filename: "{app}\main_gui.exe"; \
    WorkingDir: "{app}"; IconFilename: "{app}\Datas\TaskHere.ico"; \
    Tasks: desktopicon

[Run]
Filename: "{app}\main_gui.exe"; WorkingDir: "{app}"; \
    Description: "Launch TasksHere"; \
    Flags: nowait postinstall skipifsilent