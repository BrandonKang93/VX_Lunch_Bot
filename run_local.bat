@echo off
setlocal
cd /d %~dp0

if not exist .venv (
  python -m venv .venv
)

call .venv\Scripts\python.exe -m pip install --upgrade pip
call .venv\Scripts\python.exe -m pip install -r requirements.txt

REM 로컬 테스트용: 너무 오래 기다리지 않게 짧게 설정
if "%MAX_ATTEMPTS%"=="" set MAX_ATTEMPTS=3
if "%RETRY_SLEEP_SEC%"=="" set RETRY_SLEEP_SEC=10
if "%MAX_RUNTIME_MIN%"=="" set MAX_RUNTIME_MIN=3

REM SLACK_WEBHOOK_URL 미설정이면 main.py가 전송 스킵
echo Running with MAX_ATTEMPTS=%MAX_ATTEMPTS% RETRY_SLEEP_SEC=%RETRY_SLEEP_SEC% MAX_RUNTIME_MIN=%MAX_RUNTIME_MIN%

call .venv\Scripts\python.exe -u main.py
endlocal



