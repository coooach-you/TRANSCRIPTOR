@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Instaluji Transcriptor, chvili to potrva...
python -m venv .venv || (echo. & echo CHYBA: Python neni nainstalovany nebo neni v PATH. Viz NAVOD, krok 1. & pause & exit /b 1)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt || (echo. & echo CHYBA pri instalaci knihoven. & pause & exit /b 1)
if not exist "%USERPROFILE%\.streamlit\credentials.toml" (mkdir "%USERPROFILE%\.streamlit" 2>nul & (echo [general]& echo email = "")> "%USERPROFILE%\.streamlit\credentials.toml")
echo.
echo Hotovo! Aplikaci spustite dvojklikem na spustit.bat
pause
