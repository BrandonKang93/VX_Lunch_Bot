$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

if (-not (Test-Path ".\.venv")) {
  python -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install --upgrade pip | Out-Host
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt | Out-Host

# 로컬 테스트용: 너무 오래 기다리지 않게 짧게 설정
$env:MAX_ATTEMPTS = $env:MAX_ATTEMPTS ?? "3"
$env:RETRY_SLEEP_SEC = $env:RETRY_SLEEP_SEC ?? "10"
$env:MAX_RUNTIME_MIN = $env:MAX_RUNTIME_MIN ?? "3"

# 슬랙 안 보내고 테스트 가능(미설정이면 main.py가 전송 스킵)
# 실제 테스트하려면 아래 줄 주석 해제 후 본인 웹훅 넣으세요.
# $env:SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/...."

Write-Host "Running with MAX_ATTEMPTS=$($env:MAX_ATTEMPTS), RETRY_SLEEP_SEC=$($env:RETRY_SLEEP_SEC), MAX_RUNTIME_MIN=$($env:MAX_RUNTIME_MIN)"

& .\.venv\Scripts\python.exe -u .\main.py


