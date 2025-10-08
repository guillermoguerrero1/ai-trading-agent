# Telegram Bot Integration Setup Guide

This guide walks you through setting up the Telegram bot integration for live trade entry.

## 🚀 Quick Setup

### 1. Create a Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Choose a name for your bot (e.g., "My Trading Bot")
4. Choose a username (e.g., "my_trading_bot")
5. **Save the bot token** - you'll need this for configuration

### 2. Get Your User ID

1. Send a message to `@userinfobot` on Telegram
2. It will reply with your user ID (e.g., `123456789`)
3. **Save this user ID** for the whitelist

### 3. Configure Environment

Update your `.env` file:

```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz  # From BotFather
TELEGRAM_ALLOWED_USER_IDS=123456789,987654321              # Your user ID(s)
TELEGRAM_ENABLE=true                                        # Enable integration
TELEGRAM_WEBHOOK_URL=https://your-domain.com/v1/hooks/telegram  # Webhook URL
```

### 4. Set Up Webhook (Production)

For production, you can use the new Makefile targets:

```bash
# Using Makefile targets (recommended)
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_WEBHOOK_URL="https://your-domain.com/v1/hooks/telegram"
make telegram-webhook
```

Or manually with curl:

```bash
# Manual setup (replace with your actual domain and bot token)
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://your-domain.com/v1/hooks/telegram"}'
```

### 5. Test with ngrok (Development)

For local testing, use ngrok:

```bash
# Install ngrok (if not already installed)
# Download from https://ngrok.com/

# Start your API server
make run-api

# In another terminal, expose port 9001
ngrok http 9001

# Set webhook to ngrok URL using Makefile target
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_WEBHOOK_URL="https://abc123.ngrok.io/v1/hooks/telegram"
make telegram-webhook
```

## 📝 Trade Command Format

Send messages to your bot in this format:

```
trade NQZ5 buy 1 @ 17895 stop 17885 target 17915
```

### Command Components

- **Symbol**: Must start with `NQ` (e.g., `NQZ5`, `NQH6`)
- **Side**: `buy` or `sell`
- **Quantity**: Number of contracts (e.g., `1`, `2`)
- **Entry**: Price with `@` or `at` (e.g., `@ 17895`)
- **Stop**: Stop loss price (e.g., `stop 17885`)
- **Target**: Take profit price (optional, e.g., `target 17915`)

### Advanced Options

```
trade NQZ5 buy 1 @ 17895 stop 17885 target 17915 strat:ORB conf:0.8 at:2025-01-15T14:30:00Z
```

- **Strategy**: `strat:ORB` (strategy identifier)
- **Confidence**: `conf:0.8` (confidence level 0-1)
- **Timestamp**: `at:2025-01-15T14:30:00Z` (custom entry time)

### Example Commands

```
# Basic trade
trade NQZ5 buy 1 @ 17895 stop 17885 target 17915

# Sell trade with strategy
NQZ5 sell 2 @ 20450 stop 20460 target 20430 strat:ORB

# Trade with confidence and timestamp
/trade NQH6 buy 1 @ 18000 stop 17990 target 18020 conf:0.9 at:2025-01-15T14:30:00Z

# Trade without target (stop only)
trade NQZ5 buy 1 @ 17895 stop 17885
```

## 🔒 Security Features

### User Whitelist
Only users in `TELEGRAM_ALLOWED_USER_IDS` can place trades.

### NQ Symbol Validation
Only NQ futures symbols are allowed (NQZ5, NQH6, etc.).

### Idempotency
Each trade gets a unique `Idempotency-Key` to prevent duplicates.

### Paper Trading Default
All trades are paper trades by default for safety.

## 📊 Bot Responses

### Success Response
```
✅ Submitted NQZ5 BUY 1 @ 17895.0 stop 17885.0 target 17915.0
Idempotency-Key: tg-1696368000-abc123
```

### Error Responses
```
❌ Could not parse trade. Format: 'trade NQZ5 buy 1 @ 17895 stop 17885 target 17915 strat:ORB conf:0.7 at:2025-09-14T14:30:00Z'

❌ Only NQ symbols are allowed (e.g., NQZ5).

❌ Stop must be different from entry.

❌ Unauthorized user.
```

### Warning Messages
```
⚠️ Invalid entered_at; ignoring.
⚠️ entered_at is in the future; ignoring.
```

## 🧪 Testing

Run the test script to verify everything works:

```bash
python scripts/test_telegram_webhook.py
```

This will test:
- Trade parsing with various formats
- Error handling for invalid inputs
- Payload structure validation

## 🔧 Troubleshooting

### Bot Not Responding
1. Check `TELEGRAM_ENABLE=true` in `.env`
2. Verify bot token is correct
3. Check webhook URL is set correctly
4. Look at API server logs for errors

### "Unauthorized user" Error
1. Add your user ID to `TELEGRAM_ALLOWED_USER_IDS`
2. Get your user ID from `@userinfobot`
3. Restart the API server after changing `.env`

### Webhook Not Working
1. Use ngrok for local testing
2. Ensure webhook URL is HTTPS
3. Check that your server is accessible from internet
4. Verify webhook is set with correct URL
5. Use `make telegram-webhook` to set webhook
6. Use `make telegram-webhook-delete` to remove webhook for testing

### Parse Errors
1. Follow the exact command format
2. Use NQ symbols only
3. Include both entry and stop prices
4. Check that prices are valid numbers

## 📈 Production Deployment

### Security Checklist
- [ ] Change default `JWT_SECRET`
- [ ] Use HTTPS for webhook URL
- [ ] Limit `TELEGRAM_ALLOWED_USER_IDS` to trusted users
- [ ] Monitor bot logs for suspicious activity
- [ ] Consider rate limiting for trade commands

### Webhook Management
The Makefile includes convenient targets for webhook management:

```bash
# Set webhook URL
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_WEBHOOK_URL="https://your-domain.com/v1/hooks/telegram"
make telegram-webhook

# Remove webhook (useful for testing)
make telegram-webhook-delete

# Check webhook status (manual curl)
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

### Monitoring
- Monitor API server logs for Telegram requests
- Set up alerts for failed trades
- Track trade success/failure rates
- Monitor webhook delivery status

## 🎯 Next Steps

1. **Test thoroughly** with paper trading
2. **Add more symbols** if needed (modify regex in `telegram.py`)
3. **Implement live trading** by setting `paper: false` in payload
4. **Add more commands** like `/status`, `/positions`, `/pnl`
5. **Integrate with TradingView** for automated signals

---

**Happy Trading! 📱📈**
