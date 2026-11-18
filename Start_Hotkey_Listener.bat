@echo off
title AeroTouch - Background Hotkey Listener
color 0a
echo =====================================================================
echo         AEROTOUCH: NATIVE HOTKEY LISTENER (Ctrl + Alt + A)
echo =====================================================================
echo Listening for [Ctrl + Alt + A] globally across all Windows apps.
echo Minimize this window to keep it running silently in the background!
echo.
cd /d "%~dp0"
python -m src.service.hotkey_daemon
pause
