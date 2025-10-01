#!/bin/bash
# API Examples for AI Trading Agent

API_BASE_URL="http://localhost:8000"

echo "🤖 AI Trading Agent API Examples"
echo "================================="
echo ""

# Health Check
echo "1. Health Check"
echo "---------------"
curl -s "$API_BASE_URL/v1/health/" | jq '.'
echo ""

# Get Configuration
echo "2. Get Configuration"
echo "--------------------"
curl -s "$API_BASE_URL/v1/config/" | jq '.'
echo ""

# Update Configuration
echo "3. Update Configuration"
echo "-----------------------"
curl -s -X PUT "$API_BASE_URL/v1/config/" \
  -H "Content-Type: application/json" \
  -d '{
    "max_trades_per_day": 10,
    "daily_loss_cap_usd": 500.0,
    "session_windows": ["09:30-16:00"]
  }' | jq '.'
echo ""

# Submit Signal
echo "4. Submit Trading Signal"
echo "------------------------"
curl -s -X POST "$API_BASE_URL/v1/signal/" \
  -H "Content-Type: application/json" \
  -d '{
    "signal_type": "BUY",
    "symbol": "AAPL",
    "quantity": 100,
    "price": 150.0,
    "confidence": 0.85,
    "metadata": {
      "strategy": "momentum",
      "timeframe": "1h"
    }
  }' | jq '.'
echo ""

# Place Order
echo "5. Place Order"
echo "---------------"
curl -s -X POST "$API_BASE_URL/v1/orders/" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "side": "BUY",
    "quantity": 100,
    "order_type": "MARKET",
    "client_order_id": "example-order-001"
  }' | jq '.'
echo ""

# Get Orders
echo "6. Get Orders"
echo "-------------"
curl -s "$API_BASE_URL/v1/orders/" | jq '.'
echo ""

# Get Daily P&L
echo "7. Get Daily P&L"
echo "-----------------"
curl -s "$API_BASE_URL/v1/pnl/daily" | jq '.'
echo ""

# Get Positions
echo "8. Get Positions"
echo "----------------"
curl -s "$API_BASE_URL/v1/pnl/positions" | jq '.'
echo ""

# Get Signal Status
echo "9. Get Signal Status"
echo "--------------------"
curl -s "$API_BASE_URL/v1/signal/status" | jq '.'
echo ""

# Get P&L Summary
echo "10. Get P&L Summary"
echo "-------------------"
curl -s "$API_BASE_URL/v1/pnl/summary?period=daily" | jq '.'
echo ""

echo "✅ API Examples completed!"
echo ""
echo "📚 For more information:"
echo "   - API Documentation: $API_BASE_URL/docs"
echo "   - ReDoc: $API_BASE_URL/redoc"
echo "   - OpenAPI Spec: $API_BASE_URL/openapi.json"
