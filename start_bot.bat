@echo off
setlocal
cd /d "%~dp0"
if exist "D:\Ollama" set "PLAYWRIGHT_BROWSERS_PATH=D:\Ollama\browser"
set "BOTENV=%~dp0.venv"
if exist "D:\Ollama\bot-venv\Scripts\python.exe" set "BOTENV=D:\Ollama\bot-venv"
if exist "%BOTENV%\Scripts\python.exe" goto dependencies
py -3 -m venv .venv
if errorlevel 1 python -m venv .venv
if errorlevel 1 exit /b 2
:dependencies
if exist "%BOTENV%\setup.ok" goto ready
"%BOTENV%\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 exit /b 2
"%BOTENV%\Scripts\python.exe" -m playwright install chromium
if errorlevel 1 exit /b 2
type nul > "%BOTENV%\setup.ok"
:ready
if not "%~1"=="" goto manual
"%BOTENV%\Scripts\python.exe" run_task_bot.py --install-startup
if errorlevel 1 exit /b 2
echo Avvio formazione automatica locale. Il primo caricamento puo richiedere alcuni minuti.
echo Stato visibile qui e salvato in bot.log.
"%BOTENV%\Scripts\python.exe" -u run_task_bot.py --train-auto
exit /b %errorlevel%
:manual
"%BOTENV%\Scripts\python.exe" -u run_task_bot.py %*
exit /b %errorlevel%
