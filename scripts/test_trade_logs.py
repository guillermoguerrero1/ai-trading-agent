#!/usr/bin/env python3
"""
Regression test for trade logs endpoints
Tests GET /v1/logs/trades and GET /v1/export/trades.csv
"""

import json
import sys
import requests
from typing import Dict, Any, Optional, Tuple

# API base URL
API_URL = "http://localhost:9001"

def print_colored(text: str, color: str = "") -> None:
    """Print colored text (if terminal supports it)"""
    colors = {
        'red': '\033[0;31m',
        'green': '\033[0;32m',
        'yellow': '\033[1;33m',
        'blue': '\033[0;34m',
        'reset': '\033[0m'
    }
    if color in colors:
        try:
            print(f"{colors[color]}{text}{colors['reset']}")
        except UnicodeEncodeError:
            # Fallback for Windows console encoding issues
            print(text)
    else:
        print(text)

def check_api_health() -> bool:
    """Check if API is running and healthy"""
    try:
        response = requests.get(f"{API_URL}/v1/health", timeout=5)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException:
        return False

def test_trade_logs() -> Tuple[bool, str, int]:
    """Test GET /v1/logs/trades?limit=5 endpoint"""
    try:
        response = requests.get(f"{API_URL}/v1/logs/trades?limit=5", timeout=10)
        status_code = response.status_code
        
        if status_code in [200, 204]:
            return True, response.text, status_code
        else:
            return False, response.text, status_code
    except requests.exceptions.RequestException as e:
        return False, str(e), 0

def test_csv_export() -> Tuple[bool, str, int]:
    """Test GET /v1/export/trades.csv endpoint"""
    try:
        response = requests.get(f"{API_URL}/v1/export/trades.csv", timeout=10)
        status_code = response.status_code
        
        if status_code == 200:
            # Check if response contains CSV headers
            csv_content = response.text
            expected_headers = ["trade_id", "order_id", "symbol", "side", "quantity", "price", "timestamp"]
            has_headers = any(header in csv_content for header in expected_headers)
            
            if has_headers:
                return True, csv_content, status_code
            else:
                return False, f"Missing expected CSV headers. Content: {csv_content[:200]}...", status_code
        else:
            return False, response.text, status_code
    except requests.exceptions.RequestException as e:
        return False, str(e), 0

def main():
    """Main test function"""
    print_colored("=== Trade Logs Regression Test ===", "blue")
    print()
    
    # Check API health
    print_colored("Checking API availability...", "yellow")
    if not check_api_health():
        print_colored("Error: API is not running on " + API_URL, "red")
        print("Please start the API server first:")
        print("  make run-api")
        print("  or")
        print("  make run-docker")
        sys.exit(1)
    
    print_colored("API is running", "green")
    print()
    
    # Test results tracking
    tests_passed = 0
    tests_failed = 0
    total_tests = 2
    
    # Test 1: Trade logs endpoint
    print_colored("Test 1: GET /v1/logs/trades?limit=5", "yellow")
    print("Testing trade logs endpoint...")
    
    success, response_body, status_code = test_trade_logs()
    print(f"HTTP Status Code: {status_code}")
    
    if success:
        print_colored(f"Test 1 PASSED: Trade logs endpoint returned {status_code}", "green")
        tests_passed += 1
        
        if status_code == 200:
            print("Response body:")
            try:
                json_data = json.loads(response_body)
                print(json.dumps(json_data, indent=2))
            except json.JSONDecodeError:
                print(response_body)
        else:
            print("Response: No content (204)")
    else:
        print_colored(f"Test 1 FAILED: Trade logs endpoint returned {status_code}", "red")
        print("Response body:")
        print(response_body)
        tests_failed += 1
    
    print()
    
    # Test 2: CSV export endpoint
    print_colored("Test 2: GET /v1/export/trades.csv", "yellow")
    print("Testing CSV export endpoint...")
    
    success, response_body, status_code = test_csv_export()
    print(f"HTTP Status Code: {status_code}")
    
    if success:
        print_colored("Test 2 PASSED: CSV export endpoint returned 200 with proper headers", "green")
        tests_passed += 1
        
        print("CSV Headers found:")
        lines = response_body.split('\n')
        if lines:
            print(lines[0])
        
        print()
        print("CSV Preview (first 3 lines):")
        for i, line in enumerate(lines[:3]):
            if line.strip():
                print(line)
    else:
        print_colored(f"Test 2 FAILED: CSV export endpoint returned {status_code}", "red")
        print("Response body:")
        print(response_body[:500] + "..." if len(response_body) > 500 else response_body)
        tests_failed += 1
    
    print()
    
    # Test Summary
    print_colored("=== Test Summary ===", "blue")
    print(f"Tests Passed: {tests_passed}/{total_tests}")
    print(f"Tests Failed: {tests_failed}/{total_tests}")
    
    if tests_failed == 0:
        print_colored("All tests PASSED! Trade logs endpoints are working correctly.", "green")
        sys.exit(0)
    else:
        print_colored("Some tests FAILED! Trade logs endpoints need attention.", "red")
        print()
        print_colored("Troubleshooting tips:", "yellow")
        print("1. Check if the API server is running: make run-api")
        print("2. Check if the database has trade data: make test-order")
        print("3. Check API logs for errors")
        print("4. Verify the endpoints are properly registered in the API")
        sys.exit(1)

if __name__ == "__main__":
    main()
