<#
    WANAS — one command to a working demo.

    Brings up the whole stack, waits until the API actually answers, and prints
    what you need on screen. Written for Windows PowerShell 5.1, so no `&&`,
    no ternary operator, no null-coalescing.

    Usage:  .\scripts\demo.ps1
            .\scripts\demo.ps1 -Rebuild     # force a rebuild of the images
            .\scripts\demo.ps1 -Down        # stop everything
#>
[CmdletBinding()]
param(
    [switch]$Rebuild,
    [switch]$Down
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Write-Step($text) { Write-Host "`n=> $text" -ForegroundColor Cyan }
function Write-Ok($text)   { Write-Host "   $text" -ForegroundColor Green }
function Write-Warn($text) { Write-Host "   $text" -ForegroundColor Yellow }

if ($Down) {
    Write-Step "Stopping WANAS"
    docker compose down
    Write-Ok "Stopped. Data is preserved in the wanas_db volume."
    exit 0
}

# --- 1. Is there a Docker engine to talk to? -------------------------------
Write-Step "Checking Docker"
$engine = $null
try { $engine = docker info --format "{{.ServerVersion}}" 2>$null } catch { }
if ([string]::IsNullOrWhiteSpace($engine)) {
    Write-Host "   Docker engine is not reachable." -ForegroundColor Red
    Write-Host ""
    Write-Host "   Start Docker Desktop and wait for the whale icon to settle."
    Write-Host "   If it never starts, its Linux backend may have no WSL distribution:"
    Write-Host ""
    Write-Host "       wsl --install" -ForegroundColor White
    Write-Host ""
    Write-Host "   then reboot and run this script again."
    exit 1
}
Write-Ok "Docker engine $engine"

# --- 2. Configuration ------------------------------------------------------
Write-Step "Checking configuration"
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Ok "Created .env from .env.example"
} else {
    Write-Ok ".env present"
}

$hasKey = $false
foreach ($line in (Get-Content ".env")) {
    if ($line -match "^\s*ANTHROPIC_API_KEY\s*=\s*(.+)$") {
        if (-not [string]::IsNullOrWhiteSpace($Matches[1])) { $hasKey = $true }
    }
}
if ($hasKey) {
    Write-Ok "ANTHROPIC_API_KEY set - the guide will call Claude"
} else {
    Write-Warn "No ANTHROPIC_API_KEY - the guide runs the offline grounded provider."
    Write-Warn "That is a supported mode, not a failure: answers are composed from"
    Write-Warn "the heritage corpus and every one still carries its sources."
}

# --- 3. Bring the stack up -------------------------------------------------
Write-Step "Starting Postgres, Redis, API and web"
if ($Rebuild) { docker compose up -d --build } else { docker compose up -d }
if ($LASTEXITCODE -ne 0) {
    Write-Host "   docker compose failed - see the output above." -ForegroundColor Red
    exit 1
}

# --- 4. Wait for the API to actually answer --------------------------------
Write-Step "Waiting for the API (it seeds the database on first boot)"
$health = $null
for ($i = 1; $i -le 90; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 3
        if ($response.StatusCode -eq 200) {
            $health = $response.Content | ConvertFrom-Json
            break
        }
    } catch {
        Start-Sleep -Seconds 2
    }
}

if ($null -eq $health) {
    Write-Host "   API did not come up in 3 minutes." -ForegroundColor Red
    Write-Host "   Look at the logs:  docker compose logs api --tail 60"
    exit 1
}
Write-Ok "API healthy - provider: $($health.llm), cache: $($health.cache)"

# --- 5. Wait for the web app ----------------------------------------------
Write-Step "Waiting for the web app"
$webUp = $false
for ($i = 1; $i -le 45; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:3000/fr" -UseBasicParsing -TimeoutSec 3
        if ($r.StatusCode -eq 200) { $webUp = $true; break }
    } catch {
        Start-Sleep -Seconds 2
    }
}
if ($webUp) { Write-Ok "Web app ready" } else { Write-Warn "Web app slow to start - try http://localhost:3000 in a moment" }

# --- 6. Tell the presenter what they need ---------------------------------
Write-Host ""
Write-Host "  WANAS is running" -ForegroundColor Green
Write-Host "  ------------------------------------------------------"
Write-Host "  App          http://localhost:3000    (French)"
Write-Host "               http://localhost:3000/ar (Arabic, RTL)"
Write-Host "               http://localhost:3000/dz (Darija, RTL)"
Write-Host "  API docs     http://localhost:8000/docs"
Write-Host ""
Write-Host "  Demo accounts - password: wanas-demo-2026"
Write-Host "    visiteur@wanas.dz   traveller  - itineraries, bookings, orders"
Write-Host "    artisan@wanas.dz    artisan    - publish a product"
Write-Host "    office@wanas.dz     institution- the anonymised dashboard"
Write-Host ""
Write-Host "  Walkthrough  docs/demo-script.md  (4 minutes)"
Write-Host "  Stop         .\scripts\demo.ps1 -Down"
Write-Host "  ------------------------------------------------------"
Write-Host ""
