$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$backendDir = Join-Path $root "backend"
$frontendDir = Join-Path $root "frontend"
$venvDir = Join-Path $backendDir ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$pidFile = Join-Path $PSScriptRoot ".dev.pids"

if (Test-Path $pidFile) {
  $existingPids = Get-Content $pidFile | Where-Object { $_ -match "^\d+$" }
  foreach ($pid in $existingPids) {
    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
  }
  Remove-Item $pidFile -ErrorAction SilentlyContinue
}

Write-Host "Starting MySQL (Docker Compose)..."
& docker compose -f (Join-Path $root "infra\docker-compose.yml") up -d

Write-Host "Waiting for MySQL to be healthy..."
for ($i = 0; $i -lt 20; $i++) {
  $status = & docker inspect -f "{{.State.Health.Status}}" vibecoder-mysql 2>$null
  if ($status -eq "healthy") {
    break
  }
  Start-Sleep -Seconds 3
}

if (-not (Test-Path $venvPython)) {
  Write-Host "Creating backend virtual environment..."
  & python -m venv $venvDir
}

Write-Host "Installing backend dependencies..."
& $venvPython -m pip install -r (Join-Path $backendDir "requirements.txt")

Write-Host "Running Alembic migrations..."
Push-Location $backendDir
& $venvPython -m alembic upgrade head
Pop-Location

$backendProcess = Start-Process -FilePath $venvPython -ArgumentList @(
  "-m", "uvicorn", "app.main:app", "--reload"
) -WorkingDirectory $backendDir -PassThru

if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
  Write-Host "Installing frontend dependencies..."
  Push-Location $frontendDir
  $npmCmd = Get-Command npm -ErrorAction SilentlyContinue
  if (-not $npmCmd) {
    throw "npm not found. Please install Node.js and ensure npm is on PATH."
  }
  & $npmCmd.Source install
  Pop-Location
}

$npmCmd = Get-Command npm -ErrorAction SilentlyContinue
if (-not $npmCmd) {
  throw "npm not found. Please install Node.js and ensure npm is on PATH."
}

$frontendProcess = Start-Process -FilePath $npmCmd.Source -ArgumentList @(
  "run", "dev"
) -WorkingDirectory $frontendDir -PassThru

@($backendProcess.Id, $frontendProcess.Id) | Set-Content $pidFile

Write-Host ""
Write-Host "Backend:  http://127.0.0.1:8000"
Write-Host "Frontend: http://127.0.0.1:5173"
Write-Host "Stop with: .\scripts\stop.ps1"
