@echo off
chcp 65001 >nul
title ASCHEN MEDIA PARTNER - PUSH TO GITHUB
color 0b

echo ========================================================
echo   𓄲 ASCHEN EVENT ORGANIZER - PUSH TO GITHUB
echo   Target Repo: https://github.com/bittersheet-debug/ASCHENPATNER
echo ========================================================
echo.

set GIT_EXE=C:\Users\ADVAN\.mingit\cmd\git.exe
if not exist "%GIT_EXE%" (
    set GIT_EXE=git
)

echo [1/3] Menambahkan semua perubahan...
"%GIT_EXE%" add .
echo.

echo [2/3] Membuat commit...
"%GIT_EXE%" commit -m "feat: Media Partner ASCHEN EVENT ORGANIZER Bot, Website Portal and Vercel Deploy System"
echo.

echo ========================================================
echo   PILIHAN METODE PUSH:
echo   1. Push Biasa (Gunakan jika akun kimmyounit sudah di-invite sebagai Collaborator)
echo   2. Push menggunakan Personal Access Token (PAT) GitHub
echo ========================================================
echo.
set /p CHOICE="Pilih metode (1 atau 2): "

if "%CHOICE%"=="2" (
    echo.
    set /p GH_TOKEN="Masukkan GitHub Personal Access Token (PAT): "
    echo Sedang melakukan push dengan token...
    "%GIT_EXE%" push https://%GH_TOKEN%@github.com/bittersheet-debug/ASCHENPATNER.git main
) else (
    echo Sedang melakukan push...
    "%GIT_EXE%" push -u origin main
)

echo.
echo ========================================================
echo   SELESAI. Tekan tombol apa saja untuk keluar.
echo ========================================================
pause >nul
