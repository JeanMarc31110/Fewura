#define MyAppName "Fewura"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "JeanMarc31110"
#define MyAppExeName "Fewura.exe"

[Setup]
AppId={{B8G3F4D2-0C56-5F9B-0G2E-3B6D9C4E5F7G}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={commonpf64}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=output
OutputBaseFilename=Fewura_Setup_{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
WizardStyle=modern
UninstallDisplayName={#MyAppName}
CreateUninstallRegKey=yes
SetupLogging=yes
MinVersion=10.0.17763
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[InstallDelete]
Type: filesandordirs; Name: "{app}\*"
Type: files; Name: "{userdesktop}\Fewura.lnk"
Type: files; Name: "{commondesktop}\Fewura.lnk"
Type: files; Name: "{userprograms}\Fewura.lnk"
Type: files; Name: "{commonprograms}\Fewura.lnk"

[Files]
Source: "..\dist\Fewura\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Fewura"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\Fewura"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Fewura"; Flags: nowait postinstall skipifsilent

[Code]
procedure StopLegacyInstances();
var
  ResultCode: Integer;
begin
  Exec(ExpandConstant('{cmd}'), '/C taskkill /F /T /IM Fewura.exe >nul 2>&1', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

function InitializeSetup(): Boolean;
begin
  StopLegacyInstances();
  Result := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
    StopLegacyInstances();
end;
