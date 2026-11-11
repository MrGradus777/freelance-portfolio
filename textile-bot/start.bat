@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".env" (
    > ".env" echo BOT_TOKEN=
    >> ".env" echo MANAGER_ID=
    echo.
    echo Файл .env создан.
    echo Впишите токен от @BotFather и ваш chat_id от @userinfobot, сохраните - и запустите снова.
    echo.
    notepad ".env"
    exit /b
)

for /f "usebackq tokens=1,* delims==" %%a in (".env") do set "%%a=%%b"

set "PY=python"
python -c "import sys" >nul 2>&1
if errorlevel 1 set "PY=C:\Users\Михаил\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"

if /i not "%PY%"=="python" if not exist "%PY%" (
    echo Python не найден.
    echo Установите Python 3 с https://www.python.org/downloads/ и запустите снова.
    pause
    exit /b
)

if "%BOT_TOKEN%"=="" (
    echo В .env не заполнен BOT_TOKEN. Откройте .env и допишите.
    notepad ".env"
    exit /b
)

echo Запускаю бота... Ctrl+C - остановить.
"%PY%" bot.py
pause
