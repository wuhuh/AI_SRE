# Backup PostgreSQL database to a local file.
param(
    [string]$Container = "aisre-postgres-1",
    [string]$OutFile = "backup/aisre_$(Get-Date -Format yyyyMMdd_HHmmss).sql"
)
$root = Split-Path $PSScriptRoot -Parent
$out = Join-Path $root $OutFile
New-Item -ItemType Directory -Force -Path (Split-Path $out -Parent) | Out-Null
docker exec $Container pg_dump -U aisre -d aisre -F c -f /tmp/backup.dump
docker cp "${Container}:/tmp/backup.dump" $out
Write-Output "Backup saved to $out"