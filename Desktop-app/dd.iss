[Setup]
AppName=DataDash
AppVersion=3.3.8
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
Filename: "{cmd}"; Parameters: "/C netsh advfirewall firewall add rule name=""DataDash UDP 12345"" dir=in action=allow protocol=UDP localport=12345"; Flags: runhidden;
Filename: "{cmd}"; Parameters: "/C netsh advfirewall firewall add rule name=""DataDash UDP 12346"" dir=in action=allow protocol=UDP localport=12346"; Flags: runhidden;
Filename: "{cmd}"; Parameters: "/C netsh advfirewall firewall add rule name=""DataDash TCP 54314"" dir=in action=allow protocol=TCP localport=54314"; Flags: runhidden;
Filename: "{cmd}"; Parameters: "/C netsh advfirewall firewall add rule name=""DataDash TCP 57000"" dir=in action=allow protocol=TCP localport=57000"; Flags: runhidden;
Filename: "{cmd}"; Parameters: "/C netsh advfirewall firewall add rule name=""DataDash TCP 57341"" dir=in action=allow protocol=TCP localport=57341"; Flags: runhidden;
Filename: "{cmd}"; Parameters: "/C netsh advfirewall firewall add rule name=""DataDash TCP 58000"" dir=in action=allow protocol=TCP localport=58000"; Flags: runhidden;

[UninstallRun]
Filename: "{cmd}"; Parameters: "/C netsh advfirewall firewall delete rule name=""DataDash UDP 12345"""; Flags: runhidden;
Filename: "{cmd}"; Parameters: "/C netsh advfirewall firewall delete rule name=""DataDash UDP 12346"""; Flags: runhidden;
Filename: "{cmd}"; Parameters: "/C netsh advfirewall firewall delete rule name=""DataDash TCP 54314"""; Flags: runhidden;
Filename: "{cmd}"; Parameters: "/C netsh advfirewall firewall delete rule name=""DataDash TCP 57000"""; Flags: runhidden;
Filename: "{cmd}"; Parameters: "/C netsh advfirewall firewall delete rule name=""DataDash TCP 57341"""; Flags: runhidden;
Filename: "{cmd}"; Parameters: "/C netsh advfirewall firewall delete rule name=""DataDash TCP 58000"""; Flags: runhidden;