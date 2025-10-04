#!/bin/bash
# Cleanup script for trading agent ports
# Kills processes on ports 9001, 9012, 9014 (both local and Docker)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Ports to check
PORTS=(9001 9012 9014)

echo -e "${BLUE}=== Trading Agent Port Cleanup ===${NC}"
echo -e "Checking ports: ${PORTS[*]}"
echo ""

# Function to find processes using specific ports
find_processes_on_ports() {
    local ports=("$@")
    local processes=()
    
    for port in "${ports[@]}"; do
        # Try lsof first (more reliable on macOS/Linux)
        if command -v lsof >/dev/null 2>&1; then
            local pids=$(lsof -ti:$port 2>/dev/null || true)
            for pid in $pids; do
                if [ -n "$pid" ] && [ "$pid" != "0" ]; then
                    local cmd=$(ps -p $pid -o comm= 2>/dev/null || echo "unknown")
                    processes+=("$port:$pid:$cmd")
                fi
            done
        # Fallback to netstat
        elif command -v netstat >/dev/null 2>&1; then
            local pids=$(netstat -tlnp 2>/dev/null | grep ":$port " | awk '{print $7}' | cut -d'/' -f1 | grep -E '^[0-9]+$' || true)
            for pid in $pids; do
                if [ -n "$pid" ] && [ "$pid" != "0" ]; then
                    local cmd=$(ps -p $pid -o comm= 2>/dev/null || echo "unknown")
                    processes+=("$port:$pid:$cmd")
                fi
            done
        # Fallback to ss
        elif command -v ss >/dev/null 2>&1; then
            local pids=$(ss -tlnp | grep ":$port " | grep -o 'pid=[0-9]*' | cut -d'=' -f2 || true)
            for pid in $pids; do
                if [ -n "$pid" ] && [ "$pid" != "0" ]; then
                    local cmd=$(ps -p $pid -o comm= 2>/dev/null || echo "unknown")
                    processes+=("$port:$pid:$cmd")
                fi
            done
        fi
    done
    
    printf '%s\n' "${processes[@]}"
}

# Function to kill processes gracefully
kill_processes() {
    local processes=("$@")
    
    if [ ${#processes[@]} -eq 0 ]; then
        echo -e "${GREEN}✓ No processes found using ports ${PORTS[*]}${NC}"
        return 0
    fi
    
    echo -e "${YELLOW}Found processes using the ports:${NC}"
    echo "Port  | PID   | Process"
    echo "------|-------|--------"
    
    for process in "${processes[@]}"; do
        IFS=':' read -r port pid cmd <<< "$process"
        printf "%-5s | %-5s | %s\n" "$port" "$pid" "$cmd"
    done
    
    echo ""
    read -p "Do you want to kill these processes? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        for process in "${processes[@]}"; do
            IFS=':' read -r port pid cmd <<< "$process"
            echo -e "${YELLOW}Killing process $pid ($cmd) on port $port...${NC}"
            
            # Try graceful kill first
            if kill -TERM "$pid" 2>/dev/null; then
                # Wait a bit for graceful shutdown
                sleep 2
                # Check if still running
                if kill -0 "$pid" 2>/dev/null; then
                    echo -e "${YELLOW}Process still running, force killing...${NC}"
                    kill -9 "$pid" 2>/dev/null || true
                fi
                echo -e "${GREEN}✓ Process $pid killed${NC}"
            else
                echo -e "${RED}✗ Failed to kill process $pid${NC}"
            fi
        done
    else
        echo -e "${YELLOW}Processes left running.${NC}"
    fi
}

# Function to check and clean Docker containers
cleanup_docker() {
    echo -e "${BLUE}=== Checking Docker containers ===${NC}"
    
    if ! command -v docker >/dev/null 2>&1; then
        echo -e "${YELLOW}Docker not available, skipping Docker cleanup${NC}"
        return 0
    fi
    
    # Find containers using our ports
    local containers=$(docker ps --format "table {{.ID}}\t{{.Ports}}\t{{.Names}}" | grep -E ":(9001|9012|9014)->" || true)
    
    if [ -z "$containers" ]; then
        echo -e "${GREEN}✓ No Docker containers found using ports ${PORTS[*]}${NC}"
        return 0
    fi
    
    echo -e "${YELLOW}Found Docker containers using the ports:${NC}"
    echo "$containers"
    echo ""
    
    read -p "Do you want to stop these Docker containers? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Extract container IDs
        local container_ids=$(echo "$containers" | grep -v "CONTAINER" | awk '{print $1}' | grep -E '^[a-f0-9]+$' || true)
        
        for container_id in $container_ids; do
            if [ -n "$container_id" ]; then
                echo -e "${YELLOW}Stopping container $container_id...${NC}"
                if docker stop "$container_id" >/dev/null 2>&1; then
                    echo -e "${YELLOW}Removing container $container_id...${NC}"
                    if docker rm "$container_id" >/dev/null 2>&1; then
                        echo -e "${GREEN}✓ Container $container_id stopped and removed${NC}"
                    else
                        echo -e "${RED}✗ Failed to remove container $container_id${NC}"
                    fi
                else
                    echo -e "${RED}✗ Failed to stop container $container_id${NC}"
                fi
            fi
        done
    else
        echo -e "${YELLOW}Docker containers left running.${NC}"
    fi
}

# Main execution
main() {
    echo -e "${BLUE}Checking for processes on ports ${PORTS[*]}...${NC}"
    
    # Find processes
    local processes=($(find_processes_on_ports "${PORTS[@]}"))
    
    # Kill processes
    kill_processes "${processes[@]}"
    
    # Clean up Docker
    cleanup_docker
    
    echo ""
    echo -e "${GREEN}=== Cleanup Complete ===${NC}"
    echo -e "You can now start your trading agent on a clean port."
    echo -e "Recommended: Use port 9001 for consistency"
}

# Run main function
main "$@"
