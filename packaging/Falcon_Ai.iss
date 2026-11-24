#define MyAppName "Falcon Ai"
#define MyAppVersion "13.7.0"
#define MyAppPublisher "Falcon Ai Project"
#define MyAppExeName "Falcon Ai.exe"

[Setup]
AppId={{203A3FA9-BA0F-4685-B1B1-FA1C0F0A7C13}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
UninstallDisplayName={#MyAppName}
DefaultDirName={localappdata}\Programs\Falcon Ai
DefaultGroupName=Falcon Ai
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=none
OutputDir=output
OutputBaseFilename=Falcon_Ai_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
ChangesAssociations=no
UsePreviousAppDir=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no
UninstallDisplayIcon={app}\{#MyAppExeName}
LicenseFile=

[Files]
Source: "dist\Falcon Ai\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Tasks]
Name: "desktopicon"; Description: "Create a Falcon Ai desktop shortcut"; Flags: checkedonce

[Icons]
Name: "{autoprograms}\Falcon Ai"; Filename: "{app}\Falcon Ai.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\Falcon Ai"; Filename: "{app}\Falcon Ai.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\Falcon Ai.exe"; Description: "Launch Falcon Ai"; Flags: nowait postinstall skipifsilent
