#!/usr/bin/env python3
"""
Test script for paper order placement and fill simulation
Places a SELL order on NQZ5 and simulates a fill with price update
"""

import json
import sys
import requests
from typing import Dict, Any, Optional

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
        print(f"{colors[color]}{text}{colors['reset']}")
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

def place_order() -> Optional[Dict[Any, Any]]:
    """Place a paper SELL order on NQZ5"""
    order_data = {
        "symbol": "NQZ5",
        "side": "SELL",
        "quantity": 1,
        "order_type": "LIMIT",
        "price": 17895,
        "stop_price": 17905,
        "metadata": {
            "target": 17875,
            "paper": True
        }
    }
    
    print_colored("Order details:", "yellow")
    print(json.dumps(order_data, indent=2))
    print()
    
    try:
        response = requests.post(
            f"{API_URL}/v1/orders",
            json=order_data,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print_colored(f"Failed to place order: {e}", "red")
        return None

def send_price_update() -> Optional[Dict[Any, Any]]:
    """Send price update to simulate fill"""
    tick_data = {
        "symbol": "NQZ5",
        "price": 17874.5
    }
    
    print_colored("Price update details:", "yellow")
    print(json.dumps(tick_data, indent=2))
    print()
    
    try:
        response = requests.post(
            f"{API_URL}/v1/tick",
            json=tick_data,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print_colored(f"Failed to send price update: {e}", "red")
        return None

def check_order_status(order_id: str) -> Optional[Dict[Any, Any]]:
    """Check the status of a specific order"""
    try:
        response = requests.get(f"{API_URL}/v1/orders/{order_id}/status")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print_colored(f"Could not retrieve order status: {e}", "yellow")
        return None

def main():
    """Main test function"""
    print_colored("=== Paper Order Test Script ===", "blue")
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
    
    print_colored("✓ API is running", "green")
    print()
    
    # Step 1: Place order
    print_colored("Step 1: Placing paper SELL order on NQZ5...", "yellow")
    order_response = place_order()
    
    if not order_response:
        print_colored("✗ Failed to place order", "red")
        sys.exit(1)
    
    print_colored("✓ Order placed successfully", "green")
    print()
    print_colored("=== Order Response ===", "blue")
    print(json.dumps(order_response, indent=2))
    print()
    
    # Extract order ID
    order_id = order_response.get('order_id', '')
    if order_id:
        print_colored(f"Order ID: {order_id}", "yellow")
    print()
    
    # Step 2: Send price update
    print_colored("Step 2: Simulating fill with price update...", "yellow")
    tick_response = send_price_update()
    
    if not tick_response:
        print_colored("✗ Failed to send price update", "red")
        sys.exit(1)
    
    print_colored("✓ Price update sent successfully", "green")
    print()
    print_colored("=== Tick Response ===", "blue")
    print(json.dumps(tick_response, indent=2))
    print()
    
    # Step 3: Check order status (optional)
    if order_id:
        print_colored("Step 3: Checking order status...", "yellow")
        status_response = check_order_status(order_id)
        
        if status_response:
            print_colored("✓ Order status retrieved", "green")
            print()
            print_colored("=== Order Status ===", "blue")
            print(json.dumps(status_response, indent=2))
        else:
            print_colored("⚠ Could not retrieve order status", "yellow")
    
    print()
    print_colored("=== Test Complete ===", "green")
    print("Paper order test completed successfully!")
    print("Order: SELL 1 NQZ5 @ 17895 (stop: 17905, target: 17875)")
    print("Price update: 17874.5 (should trigger fill)")
    print()
    print_colored("You can check the order status with:", "yellow")
    if order_id:
        print(f"  curl -s {API_URL}/v1/orders/{order_id}/status | jq .")
    print(f"  curl -s {API_URL}/v1/orders | jq .")
    print(f"  curl -s {API_URL}/v1/pnl/daily | jq .")

if __name__ == "__main__":
    main()
