[Setup]
AppName=DataDash
AppVersion=3.3.2
DefaultDirName={autopf}\DataDash
DefaultGroupName=DataDash
OutputDir=Output
OutputBaseFilename=DataDashInstaller
SetupIconFile=logo.ico

[Files]
Source: "dist\DataDash.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\DataDash"; Filename: "{app}\DataDash.exe"
Name: "{group}\Uninstall DataDash"; Filename: "{uninstallexe}"

[UninstallDelete]
Type: files; Name: "{app}\*.*"
