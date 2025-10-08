# Telegram Webhook Integration

This directory contains all files related to the Telegram bot webhook integration for the AI Trading Agent.

## 📁 Directory Structure

```
telegram/
├── README.md                           # This file
├── telegram_webhook_server.py          # Main webhook server
├── setup_webhook_url.py                # Automatic webhook configuration
├── setup_telegram_webhook.py           # Interactive setup helper
├── start_telegram_with_ngrok.bat       # Automated startup script (Windows)
├── telegram_requirements.txt           # Python dependencies
├── TELEGRAM_SETUP_COMPLETE.md          # Complete setup guide
└── TELEGRAM_QUICK_START.md             # Quick reference guide
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r telegram_requirements.txt
```

### 2. Configure Environment

Add to your `.env` file:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_ALLOWED_USER_IDS=your_user_id_here
TELEGRAM_ENABLE=true
```

### 3. Run Setup

**Windows:**
```bash
cd telegram
start_telegram_with_ngrok.bat
```

**Manual (any OS):**
```bash
# Terminal 1 - Webhook Server
python telegram/telegram_webhook_server.py

# Terminal 2 - ngrok
ngrok http 8000

# Terminal 3 - Configure Webhook
python telegram/setup_webhook_url.py
```

## 📚 Documentation

- **[TELEGRAM_SETUP_COMPLETE.md](TELEGRAM_SETUP_COMPLETE.md)** - Complete setup guide with troubleshooting
- **[TELEGRAM_QUICK_START.md](TELEGRAM_QUICK_START.md)** - Quick reference guide

## 🔧 Files Description

### Core Files

- **`telegram_webhook_server.py`** - FastAPI server that receives webhooks from Telegram
  - Parses trade commands
  - Validates user permissions
  - Sends confirmation replies
  - Supports NQ futures only

- **`setup_webhook_url.py`** - Automatically configures Telegram webhook
  - Gets ngrok public URL
  - Sets webhook with Telegram API
  - Validates configuration

- **`setup_telegram_webhook.py`** - Interactive setup wizard
  - Checks ngrok installation
  - Manages webhook configuration
  - Provides setup guidance

### Helper Files

- **`start_telegram_with_ngrok.bat`** - Windows batch script
  - Starts webhook server
  - Starts ngrok tunnel
  - Configures webhook automatically

- **`telegram_requirements.txt`** - Python dependencies
  - FastAPI
  - httpx
  - pydantic
  - uvicorn

## 📋 Trade Command Format

```
trade <SYMBOL> <buy/sell> <QUANTITY> @ <ENTRY> stop <STOP> target <TARGET>
```

### Examples:
```
trade NQZ5 buy 1 @ 17895 stop 17885 target 17915
NQZ5 sell 2 @ 20450 stop 20460 target 20430
trade NQH6 buy 1 @ 18000 stop 17990 target 18020 strat:ORB conf:0.8
```

### Optional Parameters:
- `strat:NAME` - Strategy identifier
- `conf:0.8` - Confidence level (0.0-1.0)

## 🔒 Security

- **User Whitelisting**: Only configured user IDs can send trades
- **Symbol Validation**: Only NQ symbols are allowed
- **Input Validation**: All trade parameters are validated
- **Token Security**: Bot token stored in environment variables

## 🐛 Troubleshooting

See [TELEGRAM_SETUP_COMPLETE.md](TELEGRAM_SETUP_COMPLETE.md) for detailed troubleshooting steps.

### Quick Checks:

```bash
# Check if webhook server is running
netstat -ano | findstr :8000

# Check if ngrok is running  
tasklist | findstr ngrok

# View webhook status
curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo

# View ngrok dashboard
# Open: http://localhost:4040
```

## 🔄 Integration with Main System

The Telegram webhook integration is separate from the main trading API but follows the same trade format. Trades submitted via Telegram are processed through the same validation and execution pipeline.

**Main API Route**: `app/routes/telegram.py` (for production integration)  
**Standalone Server**: `telegram/telegram_webhook_server.py` (for development/testing)

## 📦 Production Deployment

For production, consider:

1. **Static Domain**: Use a domain with SSL instead of ngrok
2. **Process Manager**: Use systemd, supervisor, or PM2
3. **Monitoring**: Add logging and alerting
4. **Rate Limiting**: Implement rate limits for webhook endpoints
5. **Database**: Log all incoming trades for audit

## 📝 Notes

- **ngrok Free Tier**: URL changes on restart
- **Development Focus**: This setup is optimized for testing
- **NQ Only**: Currently restricted to NQ futures symbols
- **Windows Optimized**: Batch scripts are Windows-specific

---

For complete documentation, see the main [README.md](../README.md)

