# Telegram Webhook Quick Start Guide

## Summary
- ✅ ngrok downloaded to: `C:\Users\Owner\ngrok\ngrok.exe`
- ✅ Webhook server code ready
- ✅ Bot token configured: `8443339641:AAEODDBahaHiNI5id_Np3yqyBmVinTqha9c`

## Quick Start (Choose One Method)

### Method 1: Automated Batch File (Easiest)
```bash
start_telegram_with_ngrok.bat
```
This will:
1. Start the webhook server
2. Start ngrok tunnel
3. Configure the webhook URL automatically

### Method 2: Manual Steps
1. **Start Webhook Server** (Terminal 1):
   ```bash
   python telegram_webhook_server.py
   ```

2. **Start ngrok** (Terminal 2):
   ```bash
   C:\Users\Owner\ngrok\ngrok.exe http 8000
   ```

3. **Set Webhook URL** (Terminal 3):
   ```bash
   python setup_webhook_url.py
   ```

## Test Your Setup

Send this message to your Telegram bot:
```
trade NQZ5 buy 1 @ 17895 stop 17885 target 17915
```

You should receive a confirmation message back from the bot.

## Checking Your Previous Messages

Your two messages sent earlier were **NOT received** because the webhook wasn't configured. Once you set up the webhook using the methods above, any NEW messages you send will be received.

## Command Format

```
trade <SYMBOL> <buy/sell> <QUANTITY> @ <ENTRY> stop <STOP> target <TARGET>
```

### Examples:
- `trade NQZ5 buy 1 @ 17895 stop 17885 target 17915`
- `NQZ5 sell 2 @ 20450 stop 20460 target 20430`
- `trade NQH6 buy 1 @ 18000 stop 17990 target 18020 strat:ORB conf:0.8`

## Troubleshooting

### ngrok Not Found
If you see "ngrok not found", run:
```bash
python download_ngrok.py
```

### Webhook Server Not Responding
Check if port 8000 is in use:
```bash
netstat -ano | findstr :8000
```

### Check Webhook Status
```bash
curl https://api.telegram.org/bot8443339641:AAEODDBahaHiNI5id_Np3yqyBmVinTqha9c/getWebhookInfo
```

## What Happens Next

Once the webhook is set up:
1. You send a trade message to your Telegram bot
2. Telegram forwards it to your ngrok URL
3. ngrok tunnels it to your local webhook server (port 8000)
4. The webhook server parses the trade and logs it
5. You receive a confirmation message back

## Notes
- **ngrok free tier**: The URL changes each time you restart ngrok
- **Webhook persistence**: You'll need to re-run the setup after restarting ngrok
- **Local only**: This setup is for testing; production would use a static domain

