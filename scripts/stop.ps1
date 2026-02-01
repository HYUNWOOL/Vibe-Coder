$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pidFile = Join-Path $PSScriptRoot ".dev.pids"

if (Test-Path $pidFile) {
  $existingPids = Get-Content $pidFile | Where-Object { $_ -match "^\d+$" }
  foreach ($pid in $existingPids) {
    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
  }
  Remove-Item $pidFile -ErrorAction SilentlyContinue
} else {
  Write-Host "No PID file found. Skipping app process stop."
}

Write-Host "Stopping MySQL (Docker Compose)..."
try {
  & docker compose -f (Join-Path $root "infra\docker-compose.yml") down
} catch {
  Write-Warning "Docker Compose down failed: $($_.Exception.Message)"
}
