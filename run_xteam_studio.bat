@echo off
cd /d "%~dp0"
title Xteam Voice Studio
color 0A
echo ================================================================
echo           🌿 KHOI DONG XTEAM VOICE STUDIO (DESKTOP APP) 🌿
echo ================================================================
echo Dang khoi dong cua so phan mem Xteam Voice Studio...
python run_xteam_studio.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [Thong bao] Dang thu khoi dong lai...
    py run_xteam_studio.py
)
pause
