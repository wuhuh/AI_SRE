# Restore PostgreSQL database from a backup file.
param(
    [string]$Container = "aisre-postgres-1",
    [Parameter(Mandatory = $true)][string]$BackupFile
)
$root = Split-Path $PSScriptRoot -Parent
$backup = Join-Path $root $BackupFile
docker cp $backup "${Container}:/tmp/restore.dump"
docker exec $Container pg_restore -U aisre -d aisre --clean --if-exists /tmp/restore.dump
Write-Output "Restore completed from $backup"