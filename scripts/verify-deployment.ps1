# Verify deployment after docker compose up.
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

Write-Output "== Smoke Test =="
& .\scripts\smoke-test.ps1

Write-Output "== Docker Compose Status =="
docker compose ps

Write-Output "== Local Tests =="
python run_all_local_tests.py

Write-Output "Deployment verification complete."