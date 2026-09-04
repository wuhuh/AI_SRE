# Secret scan for common credential patterns.
$patterns = @(
    'api[_-]?key\s*=\s*["'']?[A-Za-z0-9]{16,}',
    'password\s*=\s*["'']?[A-Za-z0-9]{8,}',
    'secret\s*=\s*["'']?[A-Za-z0-9]{8,}',
    'token\s*=\s*["'']?[A-Za-z0-9]{16,}',
    'BEGIN (RSA|OPENSSH|EC) PRIVATE KEY'
)
$root = Split-Path $PSScriptRoot -Parent
$hits = Get-ChildItem -Path $root -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch 'node_modules|\.git|target|\.m2|__pycache__|\.npm-cache|\.docker' } |
    Select-String -Pattern $patterns -ErrorAction SilentlyContinue
if ($hits) {
    $hits | ForEach-Object { Write-Output "$($_.Path):$($_.LineNumber):$($_.Line)" }
    exit 1
} else {
    Write-Output "No obvious secrets found."
}