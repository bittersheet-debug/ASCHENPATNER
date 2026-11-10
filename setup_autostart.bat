@echo off
title MEDIAPATNER BOT - AUTO-START CONFIGURATOR
cd /d "%~dp0"

set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_PATH=%STARTUP_DIR%\Aschen_MediaPartner_Bot.vbs"

echo ======================================================================
echo    MEDIAPATNER BOT - PENGATURAN AUTO-START WINDOWS
echo ======================================================================
echo.
echo Direktori Startup Windows:
echo %STARTUP_DIR%
echo.

if exist "%SHORTCUT_PATH%" (
    echo [STATUS] Auto-Start saat ini: AKTIF (Sudah terpasang).
    echo.
    echo Pilihan:
    echo   [1] Hapus Auto-Start (Jangan nyala otomatis)
    echo   [2] Pasang Ulang / Perbarui Shortcut Auto-Start
    echo   [0] Batal / Keluar
    echo.
    set /p CHOICE="Pilih opsi (0/1/2): "
    if "!CHOICE!"=="1" goto REMOVE
    if "!CHOICE!"=="2" goto INSTALL
    goto EXIT
) else (
    echo [STATUS] Auto-Start saat ini: NONAKTIF.
    echo.
    echo Pilihan:
    echo   [1] Pasang Auto-Start (Bot otomatis nyala saat Windows menyala)
    echo   [0] Batal / Keluar
    echo.
    set /p CHOICE="Pilih opsi (0/1): "
    if "!CHOICE!"=="1" goto INSTALL
    goto EXIT
)

:INSTALL
echo.
echo Memasang file peluncur ke folder Startup Windows...
(
    echo Set WshShell = CreateObject^("WScript.Shell"^)
    echo WshShell.Run """" ^& "%~dp0start_background.vbs" ^& """", 0, False
    echo Set WshShell = Nothing
) > "%SHORTCUT_PATH%"

if exist "%SHORTCUT_PATH%" (
    echo [SUKSES] Auto-Start berhasil dipasang!
    echo Bot akan otomatis aktif di background setiap kali komputer dinyalakan.
) else (
    echo [GAGAL] Tidak dapat membuat file startup.
)
goto PAUSE_EXIT

:REMOVE
echo.
echo Menghapus file peluncur dari folder Startup...
del /f /q "%SHORTCUT_PATH%" >nul 2>&1
echo [SUKSES] Auto-Start berhasil dinonaktifkan.
goto PAUSE_EXIT

:PAUSE_EXIT
echo.
pause
:EXIT
