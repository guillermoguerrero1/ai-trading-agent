#!/bin/bash
# Regression test for trade logs endpoints
# Tests GET /v1/logs/trades and GET /v1/export/trades.csv

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# API base URL
API_URL="http://localhost:9001"

# Test results tracking
TESTS_PASSED=0
TESTS_FAILED=0
TOTAL_TESTS=2

echo -e "${BLUE}=== Trade Logs Regression Test ===${NC}"
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

# Test 1: GET /v1/logs/trades?limit=5
echo -e "${YELLOW}Test 1: GET /v1/logs/trades?limit=5${NC}"
echo "Testing trade logs endpoint..."

LOGS_RESPONSE=$(curl -s -w "\n%{http_code}" "$API_URL/v1/logs/trades?limit=5")
LOGS_HTTP_CODE=$(echo "$LOGS_RESPONSE" | tail -n1)
LOGS_BODY=$(echo "$LOGS_RESPONSE" | head -n -1)

echo "HTTP Status Code: $LOGS_HTTP_CODE"

if [ "$LOGS_HTTP_CODE" = "200" ] || [ "$LOGS_HTTP_CODE" = "204" ]; then
    echo -e "${GREEN}✓ Test 1 PASSED: Trade logs endpoint returned $LOGS_HTTP_CODE${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
    
    if [ "$LOGS_HTTP_CODE" = "200" ]; then
        echo "Response body:"
        if command -v jq >/dev/null 2>&1; then
            echo "$LOGS_BODY" | jq . 2>/dev/null || echo "$LOGS_BODY"
        else
            echo "$LOGS_BODY"
        fi
    else
        echo "Response: No content (204)"
    fi
else
    echo -e "${RED}✗ Test 1 FAILED: Trade logs endpoint returned $LOGS_HTTP_CODE${NC}"
    echo "Response body:"
    echo "$LOGS_BODY"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

echo ""

# Test 2: GET /v1/export/trades.csv
echo -e "${YELLOW}Test 2: GET /v1/export/trades.csv${NC}"
echo "Testing CSV export endpoint..."

CSV_RESPONSE=$(curl -s -w "\n%{http_code}" "$API_URL/v1/export/trades.csv")
CSV_HTTP_CODE=$(echo "$CSV_RESPONSE" | tail -n1)
CSV_BODY=$(echo "$CSV_RESPONSE" | head -n -1)

echo "HTTP Status Code: $CSV_HTTP_CODE"

if [ "$CSV_HTTP_CODE" = "200" ]; then
    # Check if response contains CSV headers
    if echo "$CSV_BODY" | grep -q "trade_id\|order_id\|symbol\|side\|quantity\|price\|timestamp" 2>/dev/null; then
        echo -e "${GREEN}✓ Test 2 PASSED: CSV export endpoint returned 200 with proper headers${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        
        echo "CSV Headers found:"
        echo "$CSV_BODY" | head -n 1
        echo ""
        echo "CSV Preview (first 3 lines):"
        echo "$CSV_BODY" | head -n 3
    else
        echo -e "${RED}✗ Test 2 FAILED: CSV export returned 200 but missing expected headers${NC}"
        echo "Response body:"
        echo "$CSV_BODY"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
else
    echo -e "${RED}✗ Test 2 FAILED: CSV export endpoint returned $CSV_HTTP_CODE${NC}"
    echo "Response body:"
    echo "$CSV_BODY"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

echo ""

# Test Summary
echo -e "${BLUE}=== Test Summary ===${NC}"
echo "Tests Passed: $TESTS_PASSED/$TOTAL_TESTS"
echo "Tests Failed: $TESTS_FAILED/$TOTAL_TESTS"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests PASSED! Trade logs endpoints are working correctly.${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests FAILED! Trade logs endpoints need attention.${NC}"
    echo ""
    echo -e "${YELLOW}Troubleshooting tips:${NC}"
    echo "1. Check if the API server is running: make run-api"
    echo "2. Check if the database has trade data: make test-order"
    echo "3. Check API logs for errors"
    echo "4. Verify the endpoints are properly registered in the API"
    exit 1
fi
