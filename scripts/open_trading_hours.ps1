# Open trading hours for smoke testing
# PowerShell version for Windows
# This script updates the configuration to allow trading 24/7 and disables model gate

param(
    [switch]$Help
)

if ($Help) {
    Write-Host "Open Trading Hours Script" -ForegroundColor Green
    Write-Host ""
    Write-Host "Usage:"
    Write-Host "  .\scripts\open_trading_hours.ps1           # Open trading hours"
    Write-Host "  .\scripts\open_trading_hours.ps1 -Help     # Show this help"
    Write-Host ""
    Write-Host "This script will:"
    Write-Host "  1. Check if API is running"
    Write-Host "  2. Update config to allow trading 24/7"
    Write-Host "  3. Disable model gate requirement"
    Write-Host "  4. Display current runtime configuration"
    exit 0
}

# API base URL
$API_URL = "http://localhost:9001"

Write-Host "=== Opening Trading Hours for Smoke Testing ===" -ForegroundColor Blue
Write-Host ""

# Check if API is running
Write-Host "Checking API availability..." -ForegroundColor Yellow
try {
    $healthResponse = Invoke-WebRequest -Uri "$API_URL/v1/health" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "✓ API is running" -ForegroundColor Green
} catch {
    Write-Host "Error: API is not running on $API_URL" -ForegroundColor Red
    Write-Host "Please start the API server first:"
    Write-Host "  make run-api"
    Write-Host "  or"
    Write-Host "  make run-docker"
    exit 1
}

Write-Host ""

# Update configuration to open trading hours
Write-Host "Updating configuration to open trading hours..." -ForegroundColor Yellow

$configUpdate = @{
    session_windows = @("00:00-23:59")
} | ConvertTo-Json

Write-Host "Sending configuration update:"
try {
    $configUpdate | ConvertFrom-Json | ConvertTo-Json -Depth 10
} catch {
    Write-Host $configUpdate
}
Write-Host ""

# Send PUT request to update config
Write-Host "Calling PUT /v1/config..." -ForegroundColor Yellow
try {
    $updateResponse = Invoke-WebRequest -Uri "$API_URL/v1/config" -Method PUT -Body $configUpdate -ContentType "application/json" -ErrorAction Stop
    Write-Host "✓ Configuration updated successfully" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed to update configuration: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Get and display current configuration
Write-Host "Retrieving current runtime configuration..." -ForegroundColor Yellow
Write-Host "Calling GET /v1/config..." -ForegroundColor Yellow

Write-Host ""
Write-Host "=== Current Runtime Configuration ===" -ForegroundColor Blue

try {
    $configResponse = Invoke-WebRequest -Uri "$API_URL/v1/config" -ErrorAction Stop
    $configJson = $configResponse.Content | ConvertFrom-Json
    $configJson | ConvertTo-Json -Depth 10
} catch {
    Write-Host "Error retrieving configuration: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== Trading Hours Opened Successfully ===" -ForegroundColor Green
Write-Host "Trading is now enabled 24/7 (00:00-23:59)"
Write-Host "Model gate requirement has been disabled"
Write-Host ""
Write-Host "You can now run smoke tests with:" -ForegroundColor Yellow
Write-Host "  make health"
Write-Host "  make routes"
Write-Host "  Invoke-WebRequest -Uri '$API_URL/v1/signal' -Method POST -Body '{\"signal_type\":\"BUY\",\"symbol\":\"TEST\",\"quantity\":1}' -ContentType 'application/json'"
Write-Host ""
Write-Host "To restore normal trading hours, update the config with:" -ForegroundColor Yellow
Write-Host "  Invoke-WebRequest -Uri '$API_URL/v1/config' -Method PUT -Body '{\"session_windows\":[\"06:30-08:00\",\"08:30-10:00\"]}' -ContentType 'application/json'"
