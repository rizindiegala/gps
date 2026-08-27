@echo off
cd /d "%~dp0"

if not exist "env\Scripts\python.exe" (
    echo Ambiente Python non trovato.
    echo.
    echo Esegui prima l'updater Aggiorna-GPS-Windows.exe in questa cartella,
    echo poi riprova ad avviare GPS.
    echo.
    pause
    exit /b 1
)

"env\Scripts\python.exe" app.py
if errorlevel 1 pause
