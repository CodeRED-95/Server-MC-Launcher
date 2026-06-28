#define MyAppName "Server MC Launcher"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Server MC Launcher"
#define MyAppExeName "ServerMCLauncher.exe"

[Setup]
AppId={{B6C9E5E1-4D9B-4B2A-9E1E-1D0E2F6F3F11}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=ServerMCLauncherSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Iconos adicionales:"; Flags: unchecked

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Ejecutar {#MyAppName}"; Flags: nowait postinstall skipifsilent
