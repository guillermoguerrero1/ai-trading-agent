#!/usr/bin/env bash
set -euo pipefail
FILE="${1:-trade_template.json}"
API="${API:-http://localhost:9001}"
KEY="trade-$(date +%Y%m%d-%H%M%S)-$RANDOM"

mkdir -p trades_submitted
cp "$FILE" "trades_submitted/$(basename "$FILE" .json)-$KEY.json"

echo "Submitting $FILE with Idempotency-Key: $KEY"
curl -sS -X POST "$API/v1/orders" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $KEY" \
  --data-binary "@$FILE" | jq .

