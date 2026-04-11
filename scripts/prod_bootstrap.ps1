# ARGUS Production Bootstrap — PowerShell equivalent for Windows Server deployments.
# Usage: .\scripts\prod_bootstrap.ps1
#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "=== ARGUS Production Bootstrap ===" -ForegroundColor Cyan

# 1. Check prerequisites
if (-not (Get-Command "docker" -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: docker not found" -ForegroundColor Red; exit 1
}
$composeCmd = $null
try {
    docker compose version | Out-Null
    $composeCmd = "docker compose"
} catch {
    try {
        docker-compose version | Out-Null
        $composeCmd = "docker-compose"
    } catch {
        Write-Host "ERROR: docker compose not found" -ForegroundColor Red; exit 1
    }
}

# 2. Verify .env.prod exists
if (-not (Test-Path ".env.prod")) {
    Write-Host "ERROR: .env.prod not found. Copy .env.prod.example and fill in secrets." -ForegroundColor Red
    exit 1
}

# 3. Read env and validate required vars
$envVars = @{}
Get-Content ".env.prod" | Where-Object { $_ -match "^\s*[^#].*=.*" } | ForEach-Object {
    $parts = $_ -split "=", 2
    $envVars[$parts[0].Trim()] = $parts[1].Trim()
}
$required = @("POSTGRES_PASSWORD", "REDIS_PASSWORD", "JWT_SECRET", "ADMIN_PASSWORD")
foreach ($var in $required) {
    $val = $envVars[$var]
    if (-not $val -or $val -like "CHANGE_ME*") {
        Write-Host "ERROR: $var is not set or still a placeholder in .env.prod" -ForegroundColor Red
        exit 1
    }
}
Write-Host "[OK] Secrets validated" -ForegroundColor Green

# 4. Build images
Write-Host "[..] Building Docker images..."
& docker compose -f docker-compose.prod.yml --env-file .env.prod build --no-cache
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: Image build failed"; exit 1 }
Write-Host "[OK] Images built" -ForegroundColor Green

# 5. Start infrastructure services
Write-Host "[..] Starting infrastructure services..."
& docker compose -f docker-compose.prod.yml --env-file .env.prod `
    up -d postgres redis zookeeper kafka
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: Infrastructure start failed"; exit 1 }
Write-Host "[..] Waiting 30s for infrastructure to initialise..."
Start-Sleep -Seconds 30

# 6. Run Alembic migrations
Write-Host "[..] Running database migrations..."
& docker compose -f docker-compose.prod.yml --env-file .env.prod `
    run --rm argus-api python -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: Migrations failed"; exit 1 }
Write-Host "[OK] Migrations applied" -ForegroundColor Green

# 7. Seed misinfo model weights
Write-Host "[..] Ensuring model weights are present..."
& docker compose -f docker-compose.prod.yml --env-file .env.prod `
    run --rm argus-api python -c @"
from models.misinfo.detector import detect
detect('test')
print('Misinfo model ready')
"@
if ($LASTEXITCODE -ne 0) { Write-Host "WARN: Model seed step failed (non-fatal)" -ForegroundColor Yellow }

# 8. Start all services
Write-Host "[..] Starting all services..."
& docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: Full stack start failed"; exit 1 }
Write-Host "[..] Waiting 60s for services to stabilise..."
Start-Sleep -Seconds 60

# 9. Health checks
Write-Host "[..] Running health check..."
try {
    $resp = Invoke-WebRequest -Uri "http://localhost/health" -UseBasicParsing -TimeoutSec 10
    if ($resp.StatusCode -ne 200) { throw "Unexpected status $($resp.StatusCode)" }
    Write-Host "[OK] Nginx responding" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Nginx health check failed: $_" -ForegroundColor Red; exit 1
}
try {
    $resp = Invoke-WebRequest -Uri "http://localhost/api/health" -UseBasicParsing -TimeoutSec 10
    if ($resp.StatusCode -ne 200) { throw "Unexpected status $($resp.StatusCode)" }
    Write-Host "[OK] API responding" -ForegroundColor Green
} catch {
    Write-Host "ERROR: API health check failed: $_" -ForegroundColor Red; exit 1
}

# 10. Run verify_argus.py
Write-Host "[..] Running ARGUS verification suite..."
& docker compose -f docker-compose.prod.yml --env-file .env.prod `
    exec argus-api python verify_argus.py
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: Verification failed"; exit 1 }

Write-Host ""
Write-Host "=========================================================" -ForegroundColor Green
Write-Host "ARGUS production stack is live." -ForegroundColor Green
Write-Host "  Dashboard:  http://localhost"
Write-Host "  API docs:   http://localhost/api/docs"
Write-Host "  Health:     http://localhost/health"
Write-Host "=========================================================" -ForegroundColor Green
