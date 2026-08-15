#define MyAppName "FEWURA PROSPECT"
#define MyAppVersion "1.0.2"
#define MyAppPublisher "FEWURA"
#define MyAppExeName "FEWURA_Prospect.exe"

[Setup]
AppId={{B1BE4B92-5FA2-4EF3-BE8A-E80B89911120}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\FEWURA\PROSPECT
DefaultGroupName=FEWURA\PROSPECT
OutputDir=output
OutputBaseFilename=FEWURA_PROSPECT_Setup_1.0.2
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
WizardStyle=modern
UninstallDisplayName=FEWURA PROSPECT
CreateUninstallRegKey=yes
SetupLogging=yes
MinVersion=10.0.17763
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Files]
Source: "..\dist\FEWURA_Prospect\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\FEWURA\PROSPECT"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\FEWURA PROSPECT"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le Bureau"; GroupDescription: "Raccourcis :"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Lancer FEWURA PROSPECT"; Flags: nowait postinstall skipifsilent
