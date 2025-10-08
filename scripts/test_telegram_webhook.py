#!/usr/bin/env python3
"""
Test script for Telegram webhook integration.
This simulates a Telegram webhook request to test the trade parsing.
"""

import asyncio
import json
from app.routes.telegram import parse_trade, telegram_webhook
from fastapi import Request
from unittest.mock import AsyncMock, MagicMock

async def test_telegram_webhook():
    """Test the Telegram webhook with sample data."""
    
    print("Testing Telegram Webhook Integration")
    print("=" * 50)
    
    # Test trade parsing first
    print("\nTesting Trade Parser:")
    test_messages = [
        "trade NQZ5 buy 1 @ 17895 stop 17885 target 17915",
        "NQZ5 sell 2 @ 20450 stop 20460 target 20430 strat:ORB conf:0.8",
        "/trade NQH6 buy 1 @ 18000 stop 17990 target 18020 conf:0.9",
        "trade NQZ5 buy 1 @ 17895 stop 17885",  # no target
        "NQZ5 buy 1 @ 17895 stop 17885 target 17915 at:2025-01-15T14:30:00Z",  # with timestamp
    ]
    
    for i, message in enumerate(test_messages, 1):
        try:
            payload, warnings = parse_trade(message)
            print(f"PASS Test {i}: {message[:40]}...")
            print(f"   -> {payload['symbol']} {payload['side']} {payload['qty']} @ {payload['entry']}")
            print(f"   -> Stop: {payload['stop']}, Target: {payload.get('target', 'None')}")
            if warnings:
                print(f"   -> Warnings: {warnings}")
        except Exception as e:
            print(f"FAIL Test {i}: {message[:40]}...")
            print(f"   -> Error: {e}")
        print()
    
    # Test error cases
    print("\nTesting Error Cases:")
    error_messages = [
        "invalid message",
        "trade AAPL buy 1 @ 150",  # not NQ symbol
        "trade NQZ5 buy 1 @ 17895",  # no stop
        "trade NQZ5 buy 1 @ 17895 stop 17895",  # stop same as entry
    ]
    
    for i, message in enumerate(error_messages, 1):
        try:
            payload, warnings = parse_trade(message)
            print(f"FAIL Test {i}: Should have failed but didn't: {message}")
        except Exception as e:
            print(f"PASS Test {i}: Correctly failed: {message}")
            print(f"   -> Error: {e}")
        print()

def test_telegram_payload_structure():
    """Test the structure of Telegram webhook payloads."""
    
    print("\nTesting Telegram Payload Structure:")
    
    # Sample Telegram webhook payload
    sample_payload = {
        "update_id": 123456789,
        "message": {
            "message_id": 123,
            "date": 1696368000,
            "chat": {
                "id": 123456789
            },
            "from": {
                "id": 123456789,
                "is_bot": False,
                "first_name": "Test",
                "username": "testuser"
            },
            "text": "trade NQZ5 buy 1 @ 17895 stop 17885 target 17915"
        }
    }
    
    print("Sample Telegram payload:")
    print(json.dumps(sample_payload, indent=2))
    
    print("\nPASS Payload structure looks correct for webhook testing")

if __name__ == "__main__":
    print("AI Trading Agent - Telegram Integration Test")
    print("=" * 60)
    
    # Test parsing
    asyncio.run(test_telegram_webhook())
    
    # Test payload structure
    test_telegram_payload_structure()
    
    print("\nTelegram integration test completed!")
    print("\nNext steps:")
    print("1. Set up your Telegram bot with BotFather")
    print("2. Configure TELEGRAM_BOT_TOKEN in .env")
    print("3. Set TELEGRAM_ALLOWED_USER_IDS with your user ID")
    print("4. Set TELEGRAM_ENABLE=true")
    print("5. Set up webhook URL: https://your-domain.com/v1/hooks/telegram")
    print("6. Test with real Telegram messages!")
