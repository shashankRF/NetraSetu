@echo off
setlocal

cd /d "%~dp0"

echo ==========================================
echo       HACKGRID DEVELOPMENT MODE
echo ==========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: .venv not found.
    pause
    exit /b 1
)

echo Starting backend...
start "HackGrid Backend" cmd /k "%CD%\.venv\Scripts\python.exe -m uvicorn Backend.server:app --host 127.0.0.1 --port 8000"

echo Starting frontend...
start "HackGrid Frontend" cmd /k "%CD%\.venv\Scripts\python.exe -m http.server 5500 --bind 127.0.0.1 --directory Frontend"

timeout /t 3 /nobreak >nul

start "" "http://127.0.0.1:5500"

echo.
echo HackGrid development environment started.
echo.
pause