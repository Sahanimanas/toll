@echo off
rem MLFF backend: FastAPI (ANPR platform + toll layer) on http://localhost:8000
rem Config lives in backend\.env (JWT secret, ingest key, CORS, SQLite URL).
cd /d "%~dp0..\backend"
if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] backend\.venv not found. Run scripts\setup.cmd first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
echo.
echo Backend exited. Read any error above.
pause
