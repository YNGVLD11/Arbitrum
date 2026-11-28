; Inno Setup Script for Arbitrum
#define MyAppName "Арбитрум"
#define MyAppVersion "1.5.0"
#define MyAppPublisher "YNGVLD11"
#define MyAppURL "https://github.com/YNGVLD11/Arbitrum"
#define MyAppExeName "Arbitrum.exe"
#define MyAppSourceDir "E:\Arbitrum\ArbitrReportBuilder\dist\ArbitrumApp"

[Setup]
AppId={{D88EA924-4F0E-4243-B0CF-6D1E11F9722B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={userappdata}\..\Local\Programs\Arbitrum
DisableDirPage=yes
DisableProgramGroupPage=yes
OutputBaseFilename=ArbitrumSetup
OutputDir=E:\Arbitrum\ArbitrReportBuilder\dist
SetupIconFile=E:\Arbitrum\ArbitrReportBuilder\assets\app_icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
CloseApplications=force
RestartApplications=no
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#MyAppSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
