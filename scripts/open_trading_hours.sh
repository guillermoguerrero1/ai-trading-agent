#!/bin/bash
# Open trading hours for smoke testing
# This script updates the configuration to allow trading 24/7 and disables model gate

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# API base URL
API_URL="http://localhost:9001"

echo -e "${BLUE}=== Opening Trading Hours for Smoke Testing ===${NC}"
echo ""

# Check if curl is available
if ! command -v curl >/dev/null 2>&1; then
    echo -e "${RED}Error: curl not found. Please install curl to use this script.${NC}"
    exit 1
fi

# Check if API is running
echo -e "${YELLOW}Checking API availability...${NC}"
if ! curl -s --connect-timeout 5 "$API_URL/v1/health" >/dev/null 2>&1; then
    echo -e "${RED}Error: API is not running on $API_URL${NC}"
    echo "Please start the API server first:"
    echo "  make run-api"
    echo "  or"
    echo "  make run-docker"
    exit 1
fi

echo -e "${GREEN}✓ API is running${NC}"
echo ""

# Update configuration to open trading hours
echo -e "${YELLOW}Updating configuration to open trading hours...${NC}"

CONFIG_UPDATE='{
  "session_windows": ["00:00-23:59"]
}'

echo "Sending configuration update:"
if command -v jq >/dev/null 2>&1; then
    echo "$CONFIG_UPDATE" | jq .
else
    echo "$CONFIG_UPDATE"
fi
echo ""

# Send PUT request to update config
echo -e "${YELLOW}Calling PUT /v1/config...${NC}"
if curl -s -X PUT "$API_URL/v1/config" \
    -H "Content-Type: application/json" \
    -d "$CONFIG_UPDATE" >/dev/null; then
    echo -e "${GREEN}✓ Configuration updated successfully${NC}"
else
    echo -e "${RED}✗ Failed to update configuration${NC}"
    exit 1
fi

echo ""

# Get and display current configuration
echo -e "${YELLOW}Retrieving current runtime configuration...${NC}"
echo -e "${YELLOW}Calling GET /v1/config...${NC}"

echo ""
echo -e "${BLUE}=== Current Runtime Configuration ===${NC}"

if command -v jq >/dev/null 2>&1; then
    curl -s "$API_URL/v1/config" | jq .
else
    curl -s "$API_URL/v1/config"
fi

echo ""
echo -e "${GREEN}=== Trading Hours Opened Successfully ===${NC}"
echo -e "Trading is now enabled 24/7 (00:00-23:59)"
echo -e "Model gate requirement has been disabled"
echo ""
echo -e "${YELLOW}You can now run smoke tests with:${NC}"
echo "  make health"
echo "  make routes"
echo "  curl -X POST $API_URL/v1/signal -H 'Content-Type: application/json' -d '{\"signal_type\":\"BUY\",\"symbol\":\"TEST\",\"quantity\":1}'"
echo ""
echo -e "${YELLOW}To restore normal trading hours, update the config with:${NC}"
echo "  curl -X PUT $API_URL/v1/config -H 'Content-Type: application/json' -d '{\"session_windows\":[\"06:30-08:00\",\"08:30-10:00\"]}'"
