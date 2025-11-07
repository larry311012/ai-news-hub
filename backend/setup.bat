@echo off
REM AI News Hub - Windows Setup Script
REM Double-click this file to install everything automatically!

echo ============================================================
echo   AI News Hub - Automated Setup for Windows
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed!
    echo Please download Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed!
    echo Please download Node.js from https://nodejs.org/
    pause
    exit /b 1
)

echo All prerequisites found!
echo.
echo Starting automated setup...
echo.

REM Run the Python setup script
python setup.py

if errorlevel 1 (
    echo.
    echo Setup failed! Please check the error messages above.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Setup Complete!
echo ============================================================
echo.
echo To start AI News Hub:
echo.
echo 1. Open Command Prompt in the 'backend' folder
echo    Run: venv\Scripts\activate
echo    Run: uvicorn main:app --reload --port 8000
echo.
echo 2. Open another Command Prompt in the 'frontend' folder
echo    Run: npm run dev
echo.
echo 3. Open your browser to http://localhost:3000
echo.
pause
