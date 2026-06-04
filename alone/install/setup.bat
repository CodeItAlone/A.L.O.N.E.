@echo off
title A.L.O.N.E. Installer

echo ===================================================
echo   A.L.O.N.E. Headless Assistant Windows Installer  
echo ===================================================
echo.

:: Step 1: Create local directory structure
echo [*] Creating ~/.alone/ local directories...
if not exist "%USERPROFILE%\.alone" mkdir "%USERPROFILE%\.alone"
if not exist "%USERPROFILE%\.alone\memory" mkdir "%USERPROFILE%\.alone\memory"
if not exist "..\data" mkdir "..\data"
if not exist "..\data\screenshots" mkdir "..\data\screenshots"
if not exist "..\data\generated_code" mkdir "..\data\generated_code"
echo [+] Directory structure created successfully.
echo.

:: Step 2: Install dependencies
echo [*] Installing dependencies from requirements.txt...
cd ..
call .\venv\Scripts\pip.exe install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [!] Failed to install dependencies. Please check requirements.txt.
    pause
    exit /b 1
)
echo [+] Dependencies installed successfully.
echo.

:: Step 3: Register Windows Startup Shortcut (Headless)
echo [*] Creating system startup shortcut...
set "SHORTCUT_PATH=%USERPROFILE%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\ALONE.lnk"
set "TARGET_PYTHON=%~dp0..\venv\Scripts\pythonw.exe"
set "ARGS=%~dp0..\main.py"
set "WORKING_DIR=%~dp0.."

powershell -Command "$s = (New-Object -COM WScript.Shell).CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath = '%TARGET_PYTHON%'; $s.Arguments = '%ARGS%'; $s.WorkingDirectory = '%WORKING_DIR%'; $s.WindowStyle = 7; $s.Save()"

if %ERRORLEVEL% NEQ 0 (
    echo [!] Failed to create Windows Startup shortcut.
    pause
    exit /b 1
)
echo [+] Headless startup shortcut successfully created in Windows Startup!
echo.
echo ===================================================
echo   A.L.O.N.E. Installation Complete, Sir.           
echo ===================================================
pause
