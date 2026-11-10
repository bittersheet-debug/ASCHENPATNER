@echo off
title MEDIAPATNER BOT - STATUS CHECKER
cd /d "%~dp0"

echo ======================================================================
echo    MEDIAPATNER BOT - STATUS LAYANAN & LOG RUNTIME
echo ======================================================================
echo.

set RUNNING=0
for /f "tokens=2" %%i in ('wmic process where "name='python.exe' and commandline like '%%main.py%%'" get processid 2^>nul ^| findstr /r "[0-9]"') do (
    echo [STATUS] Bot AKTIF dan sedang berjalan di background (PID: %%i)
    set RUNNING=1
)

if %RUNNING% equ 0 (
    echo [STATUS] Bot TIDAK AKTIF (Sedang berhenti)
)

echo.
echo ----------------------------------------------------------------------
echo 15 BARIS TERAKHIR DARI DATA\BOT_RUNTIME.LOG:
echo ----------------------------------------------------------------------
if exist "data\bot_runtime.log" (
    powershell -NoProfile -Command "Get-Content data\bot_runtime.log -Tail 15"
) else (
    echo Log file data\bot_runtime.log belum tersedia.
)
echo ----------------------------------------------------------------------
echo.
pause
