@echo off
echo Setting up A.L.O.N.E. for the first time...
cd /d "C:\Users\SHAN KUMAR\Desktop\ALONE\alone"

if not exist venv (
    echo [*] Creating virtual environment...
    python -m venv venv
) else (
    echo [*] Virtual environment already exists.
)

echo [*] Activating virtual environment and installing requirements...
call venv\Scripts\activate.bat
pip install -r requirements.txt

echo.
echo Setup complete, Sir! You can now launch ALONE using alone_silent_launch.vbs.
pause
