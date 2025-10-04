# Backup script for trading agent database and models
# PowerShell version for Windows

# Get current timestamp
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"

# Create backups directory if it doesn't exist
if (!(Test-Path "backups")) {
    New-Item -ItemType Directory -Path "backups"
}

if (!(Test-Path "backups/models")) {
    New-Item -ItemType Directory -Path "backups/models"
}

# Backup database
if (Test-Path "trading_agent.db") {
    $dbBackupName = "trading_agent.db.bak.$timestamp"
    Copy-Item "trading_agent.db" "backups/$dbBackupName" -ErrorAction SilentlyContinue
    Write-Host "Database backed up as: $dbBackupName"
} else {
    Write-Host "Warning: trading_agent.db not found"
}

# Backup models directory
if (Test-Path "models") {
    $modelsBackupPath = "backups/models/$timestamp"
    Copy-Item "models" $modelsBackupPath -Recurse -ErrorAction SilentlyContinue
    Write-Host "Models backed up to: $modelsBackupPath"
} else {
    Write-Host "Warning: models directory not found"
}

Write-Host "Backup completed at $(Get-Date)"
