@echo off
REM Windows (Command Prompt or double-click): set up a virtual environment and run the pipeline.
REM Usage: run.bat            (all steps)
REM        run.bat --from 3   (skip download and cleaning)
setlocal
cd /d "%~dp0"

set "PY=python"
where py >nul 2>nul
if %ERRORLEVEL%==0 set "PY=py -3"

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment in .venv ...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo Python 3 not found. Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
    goto :fail
  )
)
".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt
if errorlevel 1 goto :fail
".venv\Scripts\python.exe" scripts\run_pipeline.py %*
if errorlevel 1 goto :fail
endlocal
exit /b 0

:fail
echo.
echo The pipeline stopped with an error. See the message above.
pause
exit /b 1
