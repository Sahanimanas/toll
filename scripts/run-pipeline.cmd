@echo off
rem ANPR AI pipeline: reads each active camera, detects vehicles + plates,
rem OCRs them, and publishes recognitions to the backend (which turns them
rem into toll transactions). Requires the backend to be running on :8000.
cd /d "%~dp0..\pipeline"
if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] pipeline\.venv not found. Run scripts\setup.cmd first.
  pause
  exit /b 1
)
set ANPR_BACKEND_URL=http://127.0.0.1:8000
set PYTHONUTF8=1
".venv\Scripts\python.exe" -m anpr_pipeline.main
echo.
echo Pipeline exited. Read any error above.
pause
