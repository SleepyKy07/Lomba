@echo off
rem Tournament Scheme & Fairness Simulator — launcher Windows
rem Klik 2x file ini. Server buka di port 8000, akses dari LAN.
cd /d "%~dp0"
set PORT=8000
if not exist tournament.db (
  echo Membuat database baru: tournament.db
)
echo.
echo Menjalankan Tournament Simulator di port %PORT% (akses LAN aktif)...
echo Tekan Ctrl+C untuk berhenti, atau tutup jendela ini.
echo.
timeout /t 2 /nobreak >nul
start "" http://localhost:%PORT%
python web.py --host 0.0.0.0 --port %PORT%
pause
