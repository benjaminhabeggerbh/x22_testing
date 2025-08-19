@echo off
echo ========================================
echo    ManualCommander - X22 Device Control
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7+ from https://python.org
    pause
    exit /b 1
)

REM Check if required packages are installed
echo Checking required packages...
MISSING_PACKAGES=""

python -c "import paho.mqtt.client" >nul 2>&1
if errorlevel 1 (
    set MISSING_PACKAGES=%MISSING_PACKAGES% paho-mqtt
)

python -c "import crcmod" >nul 2>&1
if errorlevel 1 (
    set MISSING_PACKAGES=%MISSING_PACKAGES% crcmod
)

if not "%MISSING_PACKAGES%"=="" (
    echo Installing required packages: %MISSING_PACKAGES%
    pip install %MISSING_PACKAGES%
)

echo.
echo Starting ManualCommander...
echo.

REM Run the ManualCommander
python ManualCommander.py

echo.
echo ManualCommander finished.
pause
