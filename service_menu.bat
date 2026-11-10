@echo off
setlocal enabledelayedexpansion
title MEDIAPATNER BOT - CONTROL PANEL
cd /d "%~dp0"

:MENU
cls
echo ======================================================================
echo    MEDIAPATNER BOT - ASCHEN EVENT ORGANIZER
echo    PUSAT PENGENDALIAN LAYANAN PERMANEN (24/7)
echo ======================================================================
echo.

set RUNNING=0
for /f "tokens=2" %%i in ('wmic process where "name='python.exe' and commandline like '%%main.py%%'" get processid 2^>nul ^| findstr /r "[0-9]"') do (
    set RUNNING=1
    set BOT_PID=%%i
)

if %RUNNING% equ 1 (
    echo  STATUS SAAT INI : [ AKTIF BERJALAN / ONLINE ] (PID: !BOT_PID!)
) else (
    echo  STATUS SAAT INI : [ NONAKTIF / OFFLINE ]
)

set "STARTUP_FILE=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Aschen_MediaPartner_Bot.vbs"
if exist "%STARTUP_FILE%" (
    echo  AUTO-START BOOT : [ AKTIF - Otomatis Nyala Saat Komputer Dihidupkan ]
) else (
    echo  AUTO-START BOOT : [ NONAKTIF ]
)
echo ======================================================================
echo.
echo  PILIH MENU TINDAKAN:
echo.
echo   [1] Jalankan Bot di Background (Permanen + Auto-Restart jika crash)
echo   [2] Jalankan Bot dengan Jendela Terbuka (Mode Monitor / Debug)
echo   [3] Hentikan Bot (Stop Background)
echo   [4] Cek Status & Baca 15 Log Terakhir
echo   [5] Atur Auto-Start Saat Windows Menyala (Boot Startup)
echo   [6] Buka File Log Lengkap (data\bot_runtime.log)
echo   [0] Keluar dari Menu
echo.
echo ======================================================================
set /p OPT="Ketik angka pilihan (0-6) lalu tekan Enter: "

if "%OPT%"=="1" (
    echo.
    echo Menjalankan bot di background...
    wscript "%~dp0start_background.vbs"
    timeout /t 2 >nul
    goto MENU
)
if "%OPT%"=="2" (
    echo.
    echo Membuka bot dalam jendela monitor aktif...
    start "MEDIAPATNER BOT MONITOR" cmd /c "run_permanent.bat"
    goto MENU
)
if "%OPT%"=="3" (
    call "%~dp0stop_bot.bat"
    goto MENU
)
if "%OPT%"=="4" (
    call "%~dp0check_status.bat"
    goto MENU
)
if "%OPT%"=="5" (
    call "%~dp0setup_autostart.bat"
    goto MENU
)
if "%OPT%"=="6" (
    if exist "data\bot_runtime.log" (
        start notepad "data\bot_runtime.log"
    ) else (
        echo File log belum ada. Jalankan bot terlebih dahulu.
        pause
    )
    goto MENU
)
if "%OPT%"=="0" exit /b 0

goto MENU
