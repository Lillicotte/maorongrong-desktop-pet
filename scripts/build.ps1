$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
python scripts/build.py
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
