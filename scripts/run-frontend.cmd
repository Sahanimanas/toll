@echo off
rem MLFF operator console (React + Vite) on http://localhost:5173
rem Talks to the FastAPI backend on :8000 (see frontend\.env).
cd /d "%~dp0..\frontend"
if not exist node_modules (
  echo Installing frontend dependencies...
  call npm install
)
call npm run dev
echo.
echo Frontend exited. Read any error above.
pause
