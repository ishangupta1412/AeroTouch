@echo off
title AeroTouch - Spatial Hand Control
color 0b
echo =====================================================================
echo                AEROTOUCH: SPATIAL OPERATING LAYER
echo =====================================================================
echo Starting Webcam & Dual-Hand Engine...
echo Press 'q' inside the camera window anytime to exit.
echo.
cd /d "%~dp0"
python -m src.main
pause
