[Setup]
AppName=DataDash
AppVersion=3.3.4
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
; Add a firewall rule for UDP port 12346
Filename: "{cmd}"; Parameters: "/C netsh advfirewall firewall add rule name=""DataDash UDP 12346"" dir=in action=allow protocol=UDP localport=12346"; Flags: runhidden;
; Add a firewall rule for TCP ports 53000, 54000, 57000, and 58000
Filename: "{cmd}"; Parameters: "/C netsh advfirewall firewall add rule name=""DataDash TCP 53000"" dir=in action=allow protocol=TCP localport=53000"; Flags: runhidden;
Filename: "{cmd}"; Parameters: "/C netsh advfirewall firewall add rule name=""DataDash TCP 54000"" dir=in action=allow protocol=TCP localport=54000"; Flags: runhidden;
Filename: "{cmd}"; Parameters: "/C netsh advfirewall firewall add rule name=""DataDash TCP 57000"" dir=in action=allow protocol=TCP localport=57000"; Flags: runhidden;
Filename: "{cmd}"; Parameters: "/C netsh advfirewall firewall add rule name=""DataDash TCP 58000"" dir=in action=allow protocol=TCP localport=58000"; Flags: runhidden;

[UninstallRun]
; Remove the firewall rule for UDP port 12346
Filename: "{cmd}"; Parameters: "/C netsh advfirewall firewall delete rule name=""DataDash UDP 12346"""; Flags: runhidden;
; Remove the firewall rule for TCP ports 53000, 54000, 57000, and 58000
Filename: "{cmd}"; Parameters: "/C netsh advfirewall firewall delete rule name=""DataDash TCP 53000"""; Flags: runhidden;
Filename: "{cmd}"; Parameters: "/C netsh advfirewall firewall delete rule name=""DataDash TCP 54000"""; Flags: runhidden;
Filename: "{cmd}"; Parameters: "/C netsh advfirewall firewall delete rule name=""DataDash TCP 57000"""; Flags: runhidden;
Filename: "{cmd}"; Parameters: "/C netsh advfirewall firewall delete rule name=""DataDash TCP 58000"""; Flags: runhidden;