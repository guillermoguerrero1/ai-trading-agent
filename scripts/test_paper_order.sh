#!/bin/bash
# Test script for paper order placement and fill simulation
# Places a SELL order on NQZ5 and simulates a fill with price update

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# API base URL
API_URL="http://localhost:9001"

echo -e "${BLUE}=== Paper Order Test Script ===${NC}"
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

# Step 1: Place paper SELL order
echo -e "${YELLOW}Step 1: Placing paper SELL order on NQZ5...${NC}"

ORDER_DATA='{
  "symbol": "NQZ5",
  "side": "SELL",
  "quantity": 1,
  "order_type": "LIMIT",
  "price": 17895,
  "stop_price": 17905,
  "metadata": {
    "target": 17875,
    "paper": true
  }
}'

echo "Order details:"
if command -v jq >/dev/null 2>&1; then
    echo "$ORDER_DATA" | jq .
else
    echo "$ORDER_DATA"
fi
echo ""

echo -e "${YELLOW}Calling POST /v1/orders...${NC}"
ORDER_RESPONSE=$(curl -s -X POST "$API_URL/v1/orders" \
    -H "Content-Type: application/json" \
    -d "$ORDER_DATA")

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Order placed successfully${NC}"
    echo ""
    echo -e "${BLUE}=== Order Response ===${NC}"
    if command -v jq >/dev/null 2>&1; then
        echo "$ORDER_RESPONSE" | jq .
    else
        echo "$ORDER_RESPONSE"
    fi
else
    echo -e "${RED}✗ Failed to place order${NC}"
    exit 1
fi

echo ""

# Extract order ID for reference (if available)
ORDER_ID=$(echo "$ORDER_RESPONSE" | grep -o '"order_id":"[^"]*"' | cut -d'"' -f4 || echo "")
if [ -n "$ORDER_ID" ]; then
    echo -e "${YELLOW}Order ID: $ORDER_ID${NC}"
fi

echo ""

# Step 2: Simulate fill with price update
echo -e "${YELLOW}Step 2: Simulating fill with price update...${NC}"

TICK_DATA='{
  "symbol": "NQZ5",
  "price": 17874.5
}'

echo "Price update details:"
if command -v jq >/dev/null 2>&1; then
    echo "$TICK_DATA" | jq .
else
    echo "$TICK_DATA"
fi
echo ""

echo -e "${YELLOW}Calling POST /v1/tick...${NC}"
TICK_RESPONSE=$(curl -s -X POST "$API_URL/v1/tick" \
    -H "Content-Type: application/json" \
    -d "$TICK_DATA")

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Price update sent successfully${NC}"
    echo ""
    echo -e "${BLUE}=== Tick Response ===${NC}"
    if command -v jq >/dev/null 2>&1; then
        echo "$TICK_RESPONSE" | jq .
    else
        echo "$TICK_RESPONSE"
    fi
else
    echo -e "${RED}✗ Failed to send price update${NC}"
    exit 1
fi

echo ""

# Step 3: Check order status (optional)
if [ -n "$ORDER_ID" ]; then
    echo -e "${YELLOW}Step 3: Checking order status...${NC}"
    echo -e "${YELLOW}Calling GET /v1/orders/$ORDER_ID/status...${NC}"
    
    STATUS_RESPONSE=$(curl -s "$API_URL/v1/orders/$ORDER_ID/status")
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Order status retrieved${NC}"
        echo ""
        echo -e "${BLUE}=== Order Status ===${NC}"
        if command -v jq >/dev/null 2>&1; then
            echo "$STATUS_RESPONSE" | jq .
        else
            echo "$STATUS_RESPONSE"
        fi
    else
        echo -e "${YELLOW}⚠ Could not retrieve order status${NC}"
    fi
fi

echo ""
echo -e "${GREEN}=== Test Complete ===${NC}"
echo -e "Paper order test completed successfully!"
echo -e "Order: SELL 1 NQZ5 @ 17895 (stop: 17905, target: 17875)"
echo -e "Price update: 17874.5 (should trigger fill)"
echo ""
echo -e "${YELLOW}You can check the order status with:${NC}"
if [ -n "$ORDER_ID" ]; then
    echo "  curl -s $API_URL/v1/orders/$ORDER_ID/status | jq ."
fi
echo "  curl -s $API_URL/v1/orders | jq ."
echo "  curl -s $API_URL/v1/pnl/daily | jq ."
