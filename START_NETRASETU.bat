@echo off
setlocal

title HackGrid - IMC Demo

cd /d "%~dp0"

echo.
echo ==========================================
echo          HACKGRID IMC DEMO
echo ==========================================
echo.
echo Project:
echo %CD%
echo.

REM ------------------------------------------
REM Check virtual environment
REM ------------------------------------------

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Python virtual environment not found.
    echo Expected:
    echo %CD%\.venv\Scripts\python.exe
    echo.
    pause
    exit /b 1
)

set PYTHON=.venv\Scripts\python.exe

REM ------------------------------------------
REM Verify environment file
REM ------------------------------------------

if not exist ".env" (
    echo ERROR: .env file not found.
    echo.
    echo Expected:
    echo %CD%\.env
    echo.
    pause
    exit /b 1
)

echo [1/4] Environment found.
echo.

REM ------------------------------------------
REM Verify GROQ key without exposing it
REM ------------------------------------------

%PYTHON% -c "from dotenv import load_dotenv; import os; load_dotenv('.env'); raise SystemExit(0 if os.getenv('GROQ_API_KEY') else 1)"

if errorlevel 1 (
    echo ERROR: GROQ_API_KEY was not loaded from .env
    echo.
    pause
    exit /b 1
)

echo [2/4] GROQ_API_KEY loaded successfully.
echo.

REM ------------------------------------------
REM Start backend if port 8000 is not active
REM ------------------------------------------

powershell -NoProfile -Command "$c=Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue; if($c){exit 0}else{exit 1}"

if errorlevel 1 (
    echo [3/4] Starting HackGrid backend...
    start "HackGrid Backend" cmd /k "%CD%\.venv\Scripts\python.exe -m uvicorn Backend.server:app --host 127.0.0.1 --port 8000"
) else (
    echo [3/4] Backend already running on port 8000.
)

REM ------------------------------------------
REM Start frontend if port 5500 is not active
REM ------------------------------------------

powershell -NoProfile -Command "$c=Get-NetTCPConnection -LocalPort 5500 -State Listen -ErrorAction SilentlyContinue; if($c){exit 0}else{exit 1}"

if errorlevel 1 (
    echo Starting HackGrid frontend...
    start "HackGrid Frontend" cmd /k "%PYTHON% -m http.server 5500 --bind 127.0.0.1 --directory Frontend"
) else (
    echo Frontend already running on port 5500.
)

REM ------------------------------------------
REM Wait for backend
REM ------------------------------------------

echo.
echo Waiting for HackGrid backend...

set /a COUNT=0

:WAIT_BACKEND

powershell -NoProfile -Command "try{$r=Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/health' -UseBasicParsing -TimeoutSec 2;if($r.StatusCode -eq 200){exit 0}else{exit 1}}catch{exit 1}"

if not errorlevel 1 goto BACKEND_READY

set /a COUNT+=1

if %COUNT% GEQ 60 (
    echo.
    echo ERROR: Backend did not become ready.
    echo Check the HackGrid Backend terminal.
    echo.
    pause
    exit /b 1
)

timeout /t 1 /nobreak >nul
goto WAIT_BACKEND

:BACKEND_READY

echo Backend is ready.
echo.

REM ------------------------------------------
REM Wait for frontend
REM ------------------------------------------

echo Waiting for HackGrid frontend...

timeout /t 2 /nobreak >nul

echo.
echo ==========================================
echo       HACKGRID IS READY
echo ==========================================
echo.
echo Backend:
echo http://127.0.0.1:8000
echo.
echo Frontend:
echo http://127.0.0.1:5500
echo.
echo Opening HackGrid...
echo.

start "" "http://127.0.0.1:5500"

echo.
echo You can minimize this window.
echo Do NOT close the Backend or Frontend terminals.
echo.
pause