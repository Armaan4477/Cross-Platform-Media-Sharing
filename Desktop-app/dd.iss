[Setup]
AppName=DataDash
AppVersion=4.3.4
DefaultDirName={commonpf64}\DataDash
DefaultGroupName=DataDash
OutputDir=Output
OutputBaseFilename=DataDashInstaller
SetupIconFile=logo.ico
PrivilegesRequired=admin

[Files]
Source: "dist\DataDash.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\DataDash"; Filename: "{app}\DataDash.exe"
Name: "{group}\Uninstall DataDash"; Filename: "{uninstallexe}"

[UninstallDelete]
Type: files; Name: "{app}\*.*"

[Run]
Filename: "cmd.exe"; Parameters: "/C netsh advfirewall firewall delete rule name=""DataDash Full Access IN"" >nul 2>&1 & netsh advfirewall firewall add rule name=""DataDash Full Access IN"" dir=in action=allow program=""{app}\DataDash.exe"" enable=yes"; Flags: runhidden;
Filename: "cmd.exe"; Parameters: "/C netsh advfirewall firewall delete rule name=""DataDash Full Access OUT"" >nul 2>&1 & netsh advfirewall firewall add rule name=""DataDash Full Access OUT"" dir=out action=allow program=""{app}\DataDash.exe"" enable=yes"; Flags: runhidden;

[UninstallRun]
Filename: "cmd.exe"; Parameters: "/C netsh advfirewall firewall delete rule name=""DataDash Full Access IN"" >nul 2>&1"; Flags: runhidden;
Filename: "cmd.exe"; Parameters: "/C netsh advfirewall firewall delete rule name=""DataDash Full Access OUT"" >nul 2>&1"; Flags: runhidden;