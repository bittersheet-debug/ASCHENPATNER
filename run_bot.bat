@echo off
title MEDIAPATNER BOT - ASCHEN EVENT ORGANIZER
echo ======================================================================
echo    MEDIAPATNER BOT - ASCHEN EVENT ORGANIZER
echo    Automatic Media Partner Management System
echo ======================================================================
echo.
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Bot stopped with error code %ERRORLEVEL%.
    pause
)
