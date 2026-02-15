#define MyAppName "Audio DeConstruct"
#if FileExists("dist\Audio DeConstruct\Audio DeConstruct.exe")
#define MyAppVersion GetFileVersion("dist\Audio DeConstruct\Audio DeConstruct.exe")
#else
#define MyAppVersion "1.0.0"
#endif
#define MyAppPublisher "Priyanshu"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={pf}\Audio DeConstruct
DefaultGroupName=Audio DeConstruct
OutputBaseFilename=AudioDeConstructInstaller
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\Audio DeConstruct\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\Audio DeConstruct"; Filename: "{app}\Audio DeConstruct.exe"
Name: "{group}\Uninstall Audio DeConstruct"; Filename: "{uninstallexe}"
Name: "{commondesktop}\Audio DeConstruct"; Filename: "{app}\Audio DeConstruct.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"
