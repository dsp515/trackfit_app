#!/usr/bin/env pwsh
# ───────────────────────────────────────────────────────────────
#  TrackFit Ultra — Production Build Script
# ───────────────────────────────────────────────────────────────

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$FrontendDir = Join-Path $RootDir "Fitness-Implement"

Write-Host ""
Write-Host "╔══════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║    TrackFit Ultra — Production Build        ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Get LAN IP for local production testing
$lanIP = (Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.InterfaceAlias -notlike "*Loopback*" -and
                   $_.IPAddress -notlike "169.*" } |
    Select-Object -First 1).IPAddress

if (-not $lanIP) { $lanIP = "localhost" }

Write-Host "📡 Using API URL: http://${lanIP}:8000/api/v1" -ForegroundColor Yellow

# Update production env
$envLocal = @"
# Production environment
EXPO_PUBLIC_API_URL=https://trackfit-backend-bypyw43ziq-uc.a.run.app/api
EXPO_PUBLIC_DOMAIN=trackfit-backend-bypyw43ziq-uc.a.run.app
EXPO_NO_TELEMETRY=1
"@
Set-Content -Path (Join-Path $FrontendDir ".env.production") -Value $envLocal

Set-Location $FrontendDir

Write-Host "✅ Building production Android APK..." -ForegroundColor Green
Write-Host ""

& npm run eas:build:prod
