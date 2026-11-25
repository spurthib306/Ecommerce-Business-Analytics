# Windows PowerShell: set up a virtual environment and run the pipeline.
# Usage: .\run.ps1            (all steps)
#        .\run.ps1 --from 3   (skip download and cleaning)
# If scripts are blocked, run once:  Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
# or use run.bat instead.
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Host "Creating virtual environment in .venv ..."
    if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 -m venv .venv }
    elseif (Get-Command python -ErrorAction SilentlyContinue) { & python -m venv .venv }
    else { throw "Python 3 not found. Install it from https://www.python.org/downloads/ and tick 'Add python.exe to PATH'." }
}
& $venvPy -m pip install --quiet --upgrade pip
& $venvPy -m pip install --quiet -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }
& $venvPy scripts\run_pipeline.py @args
exit $LASTEXITCODE
