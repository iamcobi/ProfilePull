@echo off
echo ==========================================
echo    ProfilePull Installation Wizard
echo    Created by Chukwuebuka Obi
echo ==========================================
echo.

echo [1/3] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to PATH. 
    echo Please install Python 3.10+ and try again.
    pause
    exit /b
)

echo [2/3] Creating Python Virtual Environment (venv)...
python -m venv venv

echo [3/3] Installing Required Dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt

echo.
echo ==========================================
echo    Installation Successfully Completed!
echo    You can now double-click "run.bat"
echo    to launch the ProfilePull Server.
echo ==========================================
pause
