# Kill straggler processes and free ports for trading agent
# PowerShell version for Windows

Write-Host "=== Trading Agent Process Cleanup ===" -ForegroundColor Green

# Ports to check
$ports = @(9001, 9012, 9014)

Write-Host "`nChecking for processes using ports: $($ports -join ', ')" -ForegroundColor Yellow

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
                                $processes += [PSCustomObject]@{
                                    Port = $port
                                    PID = $pid
                                    Name = $process.ProcessName
                                    CommandLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $pid").CommandLine
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

# Find processes using our ports
$processes = Get-ProcessesByPort -PortNumbers $ports

if ($processes.Count -eq 0) {
    Write-Host "No processes found using ports $($ports -join ', ')" -ForegroundColor Green
} else {
    Write-Host "`nFound processes using the ports:" -ForegroundColor Red
    Write-Host "Port | PID  | Process Name | Command Line" -ForegroundColor Cyan
    Write-Host "-----|------|--------------|-------------" -ForegroundColor Cyan
    
    foreach ($proc in $processes) {
        Write-Host "$($proc.Port.ToString().PadRight(4)) | $($proc.PID.ToString().PadRight(4)) | $($proc.Name.PadRight(12)) | $($proc.CommandLine)" -ForegroundColor White
    }
    
    Write-Host "`nDo you want to kill these processes? (y/N): " -NoNewline -ForegroundColor Yellow
    $response = Read-Host
    
    if ($response -eq 'y' -or $response -eq 'Y') {
        foreach ($proc in $processes) {
            try {
                Write-Host "Killing process $($proc.PID) ($($proc.Name)) on port $($proc.Port)..." -ForegroundColor Yellow
                Stop-Process -Id $proc.PID -Force -ErrorAction SilentlyContinue
                Write-Host "✓ Process $($proc.PID) killed" -ForegroundColor Green
            } catch {
                Write-Host "✗ Failed to kill process $($proc.PID): $_" -ForegroundColor Red
            }
        }
    } else {
        Write-Host "Processes left running." -ForegroundColor Yellow
    }
}

# Check Docker containers
Write-Host "`n=== Checking Docker containers ===" -ForegroundColor Green

try {
    $dockerContainers = docker ps --format "table {{.ID}}\t{{.Ports}}\t{{.Names}}" 2>$null | Select-String "9001|9012|9014"
    
    if ($dockerContainers) {
        Write-Host "Found Docker containers using the ports:" -ForegroundColor Red
        Write-Host $dockerContainers -ForegroundColor White
        
        Write-Host "`nDo you want to stop these Docker containers? (y/N): " -NoNewline -ForegroundColor Yellow
        $dockerResponse = Read-Host
        
        if ($dockerResponse -eq 'y' -or $dockerResponse -eq 'Y') {
            $containerIds = $dockerContainers | ForEach-Object { ($_ -split '\s+')[0] } | Where-Object { $_ -ne "CONTAINER" }
            
            foreach ($containerId in $containerIds) {
                if ($containerId -and $containerId -ne "ID") {
                    try {
                        Write-Host "Stopping container $containerId..." -ForegroundColor Yellow
                        docker stop $containerId 2>$null
                        Write-Host "Removing container $containerId..." -ForegroundColor Yellow
                        docker rm $containerId 2>$null
                        Write-Host "✓ Container $containerId stopped and removed" -ForegroundColor Green
                    } catch {
                        Write-Host "✗ Failed to stop/remove container $containerId" -ForegroundColor Red
                    }
                }
            }
        }
    } else {
        Write-Host "No Docker containers found using ports $($ports -join ', ')" -ForegroundColor Green
    }
} catch {
    Write-Host "Docker not available or not running" -ForegroundColor Yellow
}

Write-Host "`n=== Cleanup Complete ===" -ForegroundColor Green
Write-Host "You can now start your trading agent on a clean port." -ForegroundColor Cyan
