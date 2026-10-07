#ifndef MyAppVersion
  #define MyAppVersion "0.7.2"
#endif

#define MyAppName "Insight Downloader"
#define MyAppPublisher "Insight Development"
#define MyAppExeName "Insight Downloader.exe"
#define MyAppId "InsightDevelopment.InsightDownloader.Desktop"

[Setup]
AppId={{6D327C95-E67D-49D5-8EF9-20A7785D98B6}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
VersionInfoVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\Insight Downloader
DefaultGroupName=Insight Downloader
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\release
OutputBaseFilename=InsightDownloaderSetup-v{#MyAppVersion}
SetupIconFile=..\app\assets\insight.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
UsePreviousAppDir=yes
UsePreviousGroup=yes
AppMutex={#MyAppId}

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительно:"; Flags: unchecked

[Files]
Source: "..\dist\Insight Downloader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\app\assets\insight.ico"; DestDir: "{app}"; DestName: "Insight.ico"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Insight Downloader"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\Insight.ico"; AppUserModelID: "{#MyAppId}"
Name: "{autodesktop}\Insight Downloader"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\Insight.ico"; AppUserModelID: "{#MyAppId}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Запустить Insight Downloader"; Flags: nowait postinstall skipifsilent
