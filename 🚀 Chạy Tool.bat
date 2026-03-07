@echo off
title Veo 3 Flow Automation
cd /d "%~dp0"
echo Khoi dong Veo 3 Flow Automation...
echo.
python main.py
if errorlevel 1 (
    echo.
    echo LOI! Dang cai dependencies...
    pip install selenium webdriver-manager pillow
    echo.
    python main.py
)
pause
