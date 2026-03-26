@echo off

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please run install.bat first.
    pause
    exit /b
)

if not exist venv\Scripts\activate.bat (
    echo [ERROR] Virtual Environment not found! Run install.bat first.
    pause
    exit /b
)

echo Starting ProfilePull UI Web Server...
call venv\Scripts\activate.bat
start http://127.0.0.1:5000
python app.py

pause
