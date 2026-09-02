@echo off
rem Launches the full MLFF tolling stack in three windows:
rem   1. FastAPI backend (ANPR + toll)   http://localhost:8000  (/docs for API)
rem   2. ANPR AI pipeline (live plate recognition -> toll transactions)
rem   3. Operator console (React)        http://localhost:5173
start "MLFF backend"  cmd /k "%~dp0scripts\run-backend.cmd"
timeout /t 6 /nobreak >nul
start "ANPR pipeline" cmd /k "%~dp0scripts\run-pipeline.cmd"
start "MLFF console"  cmd /k "%~dp0scripts\run-frontend.cmd"
echo.
echo All three started.
echo   Console: http://localhost:5173   (login: admin / 12345678)
echo   API:     http://localhost:8000/docs
