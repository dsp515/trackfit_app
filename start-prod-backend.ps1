#!/usr/bin/env pwsh
# ───────────────────────────────────────────────────────────────
#  TrackFit Ultra — Production Backend Start Script
# ───────────────────────────────────────────────────────────────

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $RootDir "backend"
$VenvPython = Join-Path $RootDir ".venv\Scripts\python.exe"

Write-Host ""
Write-Host "╔══════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     TrackFit Ultra — Production Backend      ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

Write-Host "🚀 Starting production backend..." -ForegroundColor Cyan

Set-Location $BackendDir

# Set production environment
$env:ENVIRONMENT = "production"
$env:PYTHONOPTIMIZE = "1"

& $VenvPython -m gunicorn app.main:app `
    --workers 4 `
    --worker-class uvicorn.workers.UvicornWorker `
    --bind 0.0.0.0:8000 `
    --timeout 120 `
    --keep-alive 5 `
    --log-level info `
    --preload