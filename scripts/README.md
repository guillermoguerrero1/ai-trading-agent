# Trading Agent Scripts

This directory contains utility scripts for managing the AI Trading Agent.

## Port Cleanup Scripts

### Purpose
Clean up processes and Docker containers using ports 9001, 9012, and 9014. This is useful when:
- Servers are stuck or not responding
- Port conflicts prevent starting new services
- Cleaning up after development sessions

### Usage

#### Option 1: Using Makefile (Recommended)
```bash
# Interactive cleanup (asks for confirmation)
make cleanup-ports

# This will automatically detect your OS and run the appropriate script
```

#### Option 2: Direct Script Execution

**On Linux/macOS:**
```bash
# Make executable (first time only)
chmod +x scripts/cleanup_ports.sh

# Run interactive cleanup
./scripts/cleanup_ports.sh

# The script will:
# 1. Find processes using ports 9001, 9012, 9014
# 2. Show process details (PID, name, command line)
# 3. Ask for confirmation before killing
# 4. Kill processes gracefully (SIGTERM, then SIGKILL if needed)
# 5. Check and clean Docker containers using those ports
```

**On Windows:**
```powershell
# Interactive cleanup
.\scripts\cleanup_ports.ps1

# Skip confirmations (force mode)
.\scripts\cleanup_ports.ps1 -Force

# Show help
.\scripts\cleanup_ports.ps1 -Help
```

### What the Scripts Do

1. **Process Detection**: Uses `lsof`/`netstat`/`ss` to find processes listening on the target ports
2. **Process Information**: Shows PID, process name, and command line for each process
3. **Graceful Termination**: Attempts graceful shutdown (SIGTERM) before force killing (SIGKILL)
4. **Docker Cleanup**: Identifies and stops Docker containers using the target ports
5. **Interactive Confirmation**: Asks before taking destructive actions (unless using `-Force`)

### Ports Cleaned

- **9001**: Primary API port (recommended for trading agent)
- **9012**: Alternative API port
- **9014**: Alternative API port

### Safety Features

- **Confirmation Prompts**: Scripts ask before killing processes
- **Graceful Shutdown**: Attempts graceful termination before force killing
- **Error Handling**: Continues even if some processes can't be killed
- **Process Validation**: Verifies processes are still running before attempting to kill them

### Troubleshooting

**Script not found error:**
```bash
# Ensure scripts directory exists and is in the project root
ls scripts/
# Should show: cleanup_ports.sh and cleanup_ports.ps1
```

**Permission denied (Linux/macOS):**
```bash
chmod +x scripts/cleanup_ports.sh
```

**PowerShell execution policy (Windows):**
```powershell
# If you get execution policy errors, run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# Or use the Makefile which handles this automatically
```

**Docker not found:**
- Scripts will skip Docker cleanup if Docker is not available
- This is normal if you're not using Docker

### Examples

**Clean up after a stuck uvicorn server:**
```bash
make cleanup-ports
# Shows: Found process on port 9001 (PID 12345, uvicorn)
# Asks: Do you want to kill these processes? (y/N): y
# Result: Process killed, port 9001 is now free
```

**Clean up Docker containers:**
```bash
make cleanup-ports
# Shows: Found Docker container using port 9001
# Asks: Do you want to stop these Docker containers? (y/N): y
# Result: Container stopped and removed
```

**Force cleanup (skip confirmations):**
```powershell
.\scripts\cleanup_ports.ps1 -Force
# Kills all processes without asking
```

### Integration with Development Workflow

The cleanup scripts are designed to work seamlessly with the trading agent development workflow:

1. **Before starting servers**: Run `make cleanup-ports` to ensure clean ports
2. **After development**: Run `make cleanup-ports` to clean up
3. **In CI/CD**: Use `-Force` flag for automated cleanup
4. **Troubleshooting**: Use when servers won't start due to port conflicts

### Recommended Usage

```bash
# Start your development session
make cleanup-ports  # Clean up any leftover processes
make run-api        # Start your API server on port 9001

# End your development session  
make cleanup-ports  # Clean up when done
```
