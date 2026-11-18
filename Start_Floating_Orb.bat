@echo off
title AeroTouch - Floating Orb Mode
color 0b
echo =====================================================================
echo          AEROTOUCH: AMBIENT FLOATING ORB (GEMINI LIVE STYLE)
echo =====================================================================
echo Starting Ambient Circular Glass Orb...
echo Drag the circular orb anywhere on your screen!
echo Press Ctrl + C in this window to stop.
echo.
cd /d "%~dp0"
python -m src.main --orb
pause
