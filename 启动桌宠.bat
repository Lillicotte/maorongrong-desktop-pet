@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist "dist\猫溶溶\猫溶溶.exe" (
  start "" "dist\猫溶溶\猫溶溶.exe"
) else (
  pythonw app.py
)
