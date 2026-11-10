@echo off
title MEDIAPATNER BOT - STOPPER
cd /d "%~dp0"

echo ======================================================================
echo    MEDIAPATNER BOT - Menghentikan Layanan Background
echo ======================================================================
echo.

:: Cari proses python yang menjalankan main.py
set FOUND=0
for /f "tokens=2" %%i in ('wmic process where "name='python.exe' and commandline like '%%main.py%%'" get processid 2^>nul ^| findstr /r "[0-9]"') do (
    echo Menghentikan proses PID %%i...
    taskkill /pid %%i /f >nul 2>&1
    set FOUND=1
)

:: Hentikan juga instance cmd.exe watchdog runner jika ada
for /f "tokens=2" %%i in ('wmic process where "name='cmd.exe' and commandline like '%%run_permanent.bat%%'" get processid 2^>nul ^| findstr /r "[0-9]"') do (
    echo Menghentikan watchdog PID %%i...
    taskkill /pid %%i /f >nul 2>&1
    set FOUND=1
)

if %FOUND% equ 1 (
    echo.
    echo [SUKSES] Seluruh proses bot background telah dihentikan.
) else (
    echo.
    echo [INFO] Tidak ada proses bot background yang sedang berjalan.
)

echo.
timeout /t 3
