[Setup]
AppName=AleksBot Early Access
AppVersion=1.0
DefaultDirName={pf}\AleksBot
DefaultGroupName=AleksBot
OutputBaseFilename=AleksBot_Installer_v1_0
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64

[Files]
; ---- App principal ----
Source: "App\aleksbot.py"; DestDir: "{app}\App"; Flags: ignoreversion
Source: "App\AleksLauncher.exe"; DestDir: "{app}\App"; Flags: ignoreversion
Source: "App\icon.ico"; DestDir: "{app}\App"; Flags: ignoreversion

; ---- Instaladores externos ----
Source: "python-3.14.0-amd64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "tesseract-ocr-w64-setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{group}\AleksBot"; Filename: "{app}\App\AleksLauncher.exe"
Name: "{userdesktop}\AleksBot"; Filename: "{app}\App\AleksLauncher.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; Flags: unchecked

[Run]
; ---- Verificar Python ----
Filename: "{tmp}\python-3.14.0-amd64.exe"; \
    Parameters: "/quiet InstallAllUsers=1 PrependPath=1"; \
    StatusMsg: "Instalando Python 3.14..."; \
    Check: not PythonInstalled

; ---- Verificar Tesseract ----
Filename: "{tmp}\tesseract-ocr-w64-setup.exe"; \
    Parameters: "/SILENT"; \
    StatusMsg: "Instalando Tesseract OCR..."; \
    Check: not TesseractInstalled

; ---- Ejecutar launcher al final ----
Filename: "{app}\App\AleksLauncher.exe"; \
    Description: "Abrir AleksBot ahora"; \
    Flags: postinstall nowait skipifsilent

[Code]
function PythonInstalled(): Boolean;
begin
  Result := FileExists(ExpandConstant('{cmd}\python.exe'));
end;

function TesseractInstalled(): Boolean;
begin
  Result := FileExists('C:\Program Files\Tesseract-OCR\tesseract.exe');
end;
