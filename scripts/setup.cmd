@echo off
rem One-time setup: creates both Python virtualenvs and installs frontend deps.
rem Only needed on a fresh clone - the venvs are build artifacts, not source.
rem NOTE: the pipeline installs torch/ultralytics/easyocr (several GB).

echo === backend venv ===
cd /d "%~dp0..\backend"
if not exist ".venv\Scripts\python.exe" python -m venv .venv
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt

echo.
echo === pipeline venv (large: torch + CUDA) ===
cd /d "%~dp0..\pipeline"
if not exist ".venv\Scripts\python.exe" python -m venv .venv
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
echo.
echo For real-time accuracy the pipeline also needs the AI backends:
echo   .venv\Scripts\python.exe -m pip install ultralytics easyocr
echo (GPU: install a CUDA build of torch from https://pytorch.org)

echo.
echo === frontend deps ===
cd /d "%~dp0..\frontend"
call npm install

echo.
echo Setup complete. Run start.cmd from the project root.
pause
