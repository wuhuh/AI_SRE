# Smoke test after deployment.
$ErrorActionPreference = "Stop"

$checks = @(
    @{Name="Control Plane"; Url="http://localhost:8080/health"},
    @{Name="Agent Runtime"; Url="http://localhost:8081/health"},
    @{Name="Tool Server"; Url="http://localhost:8082/health"},
    @{Name="Frontend"; Url="http://localhost:8083"},
    @{Name="Prometheus"; Url="http://localhost:9090/-/healthy"},
    @{Name="Grafana"; Url="http://localhost:3000/api/health"}
)

foreach ($c in $checks) {
    try {
        $r = Invoke-WebRequest -Uri $c.Url -UseBasicParsing -TimeoutSec 5
        Write-Output "$($c.Name): OK ($($r.StatusCode))"
    } catch {
        Write-Error "$($c.Name): FAILED - $($_.Exception.Message)"
        exit 1
    }
}
Write-Output "Smoke test passed."