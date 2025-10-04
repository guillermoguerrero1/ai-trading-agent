# Cleanup script for trading agent ports
# PowerShell version for Windows
# Kills processes on ports 9001, 9012, 9014 (both local and Docker)

param(
    [switch]$Force,
    [switch]$Help
)

if ($Help) {
    Write-Host "Trading Agent Port Cleanup Script" -ForegroundColor Green
    Write-Host ""
    Write-Host "Usage:"
    Write-Host "  .\scripts\cleanup_ports.ps1           # Interactive mode"
    Write-Host "  .\scripts\cleanup_ports.ps1 -Force    # Skip confirmations"
    Write-Host "  .\scripts\cleanup_ports.ps1 -Help     # Show this help"
    Write-Host ""
    Write-Host "This script will:"
    Write-Host "  1. Find processes using ports 9001, 9012, 9014"
    Write-Host "  2. Show process details"
    Write-Host "  3. Kill processes gracefully (with confirmation unless -Force)"
    Write-Host "  4. Check and clean Docker containers using those ports"
    exit 0
}

# Ports to check
$PORTS = @(9001, 9012, 9014)

Write-Host "=== Trading Agent Port Cleanup ===" -ForegroundColor Green
Write-Host "Checking ports: $($PORTS -join ', ')" -ForegroundColor Cyan
Write-Host ""

# Function to find processes using specific ports
function Get-ProcessesByPort {
    param([int[]]$PortNumbers)
    
    $processes = @()
    
    foreach ($port in $PortNumbers) {
        try {
            # Use netstat to find processes using the port
            $netstatOutput = netstat -ano | Select-String ":$port.*LISTENING"
            
            foreach ($line in $netstatOutput) {
                $parts = $line.ToString().Split() | Where-Object { $_ -ne "" }
                if ($parts.Length -ge 5) {
                    $pid = $parts[-1]
                    if ($pid -match '^\d+$') {
                        try {
                            $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
                            if ($process) {
                                $commandLine = ""
                                try {
                                    $wmiProcess = Get-WmiObject Win32_Process -Filter "ProcessId = $pid" -ErrorAction SilentlyContinue
                                    if ($wmiProcess) {
                                        $commandLine = $wmiProcess.CommandLine
                                    }
                                } catch {
                                    # Ignore WMI errors
                                }
                                
                                $processes += [PSCustomObject]@{
                                    Port = $port
                                    PID = $pid
                                    Name = $process.ProcessName
                                    CommandLine = $commandLine
                                }
                            }
                        } catch {
                            # Process might have ended
                        }
                    }
                }
            }
        } catch {
            Write-Warning "Error checking port $port : $_"
        }
    }
    
    return $processes
}

# Function to kill processes gracefully
function Stop-ProcessesGracefully {
    param([array]$Processes, [bool]$ForceKill = $false)
    
    if ($Processes.Count -eq 0) {
        Write-Host "✓ No processes found using ports $($PORTS -join ', ')" -ForegroundColor Green
        return
    }
    
    Write-Host "Found processes using the ports:" -ForegroundColor Yellow
    Write-Host "Port  | PID   | Process Name | Command Line" -ForegroundColor Cyan
    Write-Host "------|-------|--------------|-------------" -ForegroundColor Cyan
    
    foreach ($proc in $Processes) {
        $cmdLine = if ($proc.CommandLine) { $proc.CommandLine.Substring(0, [Math]::Min(50, $proc.CommandLine.Length)) + "..." } else { "N/A" }
        Write-Host "$($proc.Port.ToString().PadRight(5)) | $($proc.PID.ToString().PadRight(5)) | $($proc.Name.PadRight(12)) | $cmdLine" -ForegroundColor White
    }
    
    if (-not $ForceKill) {
        Write-Host ""
        Write-Host "Do you want to kill these processes? (y/N): " -NoNewline -ForegroundColor Yellow
        $response = Read-Host
        
        if ($response -ne 'y' -and $response -ne 'Y') {
            Write-Host "Processes left running." -ForegroundColor Yellow
            return
        }
    }
    
    foreach ($proc in $Processes) {
        try {
            Write-Host "Killing process $($proc.PID) ($($proc.Name)) on port $($proc.Port)..." -ForegroundColor Yellow
            
            # Try graceful termination first
            $process = Get-Process -Id $proc.PID -ErrorAction SilentlyContinue
            if ($process) {
                $process.CloseMainWindow() | Out-Null
                Start-Sleep -Seconds 2
                
                # Check if still running
                if (-not $process.HasExited) {
                    Write-Host "Process still running, force killing..." -ForegroundColor Yellow
                    Stop-Process -Id $proc.PID -Force -ErrorAction SilentlyContinue
                }
                Write-Host "✓ Process $($proc.PID) killed" -ForegroundColor Green
            } else {
                Write-Host "Process $($proc.PID) already terminated" -ForegroundColor Green
            }
        } catch {
            Write-Host "✗ Failed to kill process $($proc.PID): $_" -ForegroundColor Red
        }
    }
}

# Function to check and clean Docker containers
function Stop-DockerContainers {
    param([bool]$ForceKill = $false)
    
    Write-Host "`n=== Checking Docker containers ===" -ForegroundColor Green
    
    try {
        $dockerContainers = docker ps --format "table {{.ID}}\t{{.Ports}}\t{{.Names}}" 2>$null | Select-String "9001|9012|9014"
        
        if (-not $dockerContainers) {
            Write-Host "✓ No Docker containers found using ports $($PORTS -join ', ')" -ForegroundColor Green
            return
        }
        
        Write-Host "Found Docker containers using the ports:" -ForegroundColor Yellow
        Write-Host $dockerContainers -ForegroundColor White
        
        if (-not $ForceKill) {
            Write-Host ""
            Write-Host "Do you want to stop these Docker containers? (y/N): " -NoNewline -ForegroundColor Yellow
            $response = Read-Host
            
            if ($response -ne 'y' -and $response -ne 'Y') {
                Write-Host "Docker containers left running." -ForegroundColor Yellow
                return
            }
        }
        
        $containerIds = $dockerContainers | ForEach-Object { 
            $parts = $_ -split '\s+'
            if ($parts[0] -and $parts[0] -ne "CONTAINER" -and $parts[0] -match '^[a-f0-9]+$') {
                $parts[0]
            }
        } | Where-Object { $_ }
        
        foreach ($containerId in $containerIds) {
            try {
                Write-Host "Stopping container $containerId..." -ForegroundColor Yellow
                if (docker stop $containerId 2>$null) {
                    Write-Host "Removing container $containerId..." -ForegroundColor Yellow
                    if (docker rm $containerId 2>$null) {
                        Write-Host "✓ Container $containerId stopped and removed" -ForegroundColor Green
                    } else {
                        Write-Host "✗ Failed to remove container $containerId" -ForegroundColor Red
                    }
                } else {
                    Write-Host "✗ Failed to stop container $containerId" -ForegroundColor Red
                }
            } catch {
                Write-Host "✗ Error with container $containerId : $_" -ForegroundColor Red
            }
        }
    } catch {
        Write-Host "Docker not available or not running" -ForegroundColor Yellow
    }
}

# Main execution
try {
    Write-Host "Checking for processes on ports $($PORTS -join ', ')..." -ForegroundColor Cyan
    
    # Find processes
    $processes = Get-ProcessesByPort -PortNumbers $PORTS
    
    # Kill processes
    Stop-ProcessesGracefully -Processes $processes -ForceKill $Force
    
    # Clean up Docker
    Stop-DockerContainers -ForceKill $Force
    
    Write-Host ""
    Write-Host "=== Cleanup Complete ===" -ForegroundColor Green
    Write-Host "You can now start your trading agent on a clean port." -ForegroundColor Cyan
    Write-Host "Recommended: Use port 9001 for consistency" -ForegroundColor Cyan
    
} catch {
    Write-Host "Error during cleanup: $_" -ForegroundColor Red
    exit 1
}
