# Telegram Webhook Setup - Complete Guide

## ✅ What's Been Done

1. **Downloaded ngrok**: Located at `C:\Users\Owner\ngrok\ngrok.exe`
2. **Fixed bot token**: Corrected to `8443339641:AAEODDBahaHiNI5id_Np3yqyBmVinTqha9c`
3. **Created automation scripts**: Ready to start webhook server and ngrok
4. **Webhook server ready**: `telegram_webhook_server.py` configured and tested

## 🚀 How to Start Everything

### Option 1: Run the Batch File (Easiest)
Double-click or run from terminal:
```bash
start_telegram_with_ngrok.bat
```

This will:
- Open a window with the webhook server
- Open a window with ngrok tunnel
- Automatically configure the webhook URL with Telegram

### Option 2: Manual Setup (More Control)

1. **Terminal 1 - Start Webhook Server**:
   ```bash
   cd "C:\Users\Owner\Trading AI Agent\ai-trading-agent"
   python telegram_webhook_server.py
   ```
   You should see: "Starting Telegram Webhook Server..."

2. **Terminal 2 - Start ngrok**:
   ```bash
   C:\Users\Owner\ngrok\ngrok.exe http 8000
   ```
   You should see a dashboard with your public HTTPS URL

3. **Terminal 3 - Configure Webhook**:
   ```bash
   cd "C:\Users\Owner\Trading AI Agent\ai-trading-agent"
   python setup_webhook_url.py
   ```
   This automatically gets the ngrok URL and sets up the webhook

## 📨 About Your Two Previous Messages

**Status**: Your two messages sent earlier were **NOT received** because:
- No webhook was configured at the time
- Telegram needs a webhook URL to forward messages
- Without it, messages go nowhere

**Solution**: Once you run the setup above, send NEW messages and they will be received.

## 🧪 Testing the Setup

1. **Start everything** using one of the options above

2. **Verify it's working**:
   - Webhook server window should show "Uvicorn running on..."
   - ngrok window should show "Forwarding https://xxxxx.ngrok.io -> http://localhost:8000"
   - Setup script should say "Webhook set successfully!"

3. **Send a test trade** to your Telegram bot:
   ```
   trade NQZ5 buy 1 @ 17895 stop 17885 target 17915
   ```

4. **Check for response**:
   - Bot should reply with: "✅ Submitted NQZ5 BUY 1 @ 17895.0 stop 17885.0 target 17915.0"
   - Webhook server window will show the incoming message

## 📋 Trade Command Format

```
trade <SYMBOL> <BUY/SELL> <QTY> @ <ENTRY> stop <STOP> target <TARGET>
```

### Examples:
- `trade NQZ5 buy 1 @ 17895 stop 17885 target 17915`
- `NQZ5 sell 2 @ 20450 stop 20460 target 20430`
- `trade NQH6 buy 1 @ 18000 stop 17990 target 18020 strat:ORB conf:0.8`

### Optional Parameters:
- `strat:ORB` - Strategy name
- `conf:0.8` - Confidence level (0.0-1.0)

## 🔍 Troubleshooting

### Check if Webhook Server is Running
```bash
netstat -ano | findstr :8000
```
Should show: `LISTENING       [PID]`

### Check if ngrok is Running
```bash
tasklist | findstr ngrok
```
Should show: `ngrok.exe        [PID] Console`

### Check Webhook Status
```bash
curl https://api.telegram.org/bot8443339641:AAEODDBahaHiNI5id_Np3yqyBmVinTqha9c/getWebhookInfo
```

### View ngrok Dashboard
Open in browser: `http://localhost:4040`

### Kill Processes if Needed
```bash
# Kill webhook server
taskkill /F /PID [PID from netstat]

# Kill ngrok
taskkill /F /IM ngrok.exe
```

## ⚠️ Important Notes

1. **ngrok Free Tier**: URL changes every restart
   - You'll need to re-run the setup after restarting ngrok
   - The webhook URL will be different each time

2. **Keep Windows Open**: Don't close the webhook server or ngrok windows

3. **Development Only**: This setup is for testing
   - Production would use a static domain
   - Consider ngrok paid plan or own server for production

4. **Security**: Only your Telegram user ID (6122478067) can use the bot

## 📁 Files Created

- `C:\Users\Owner\ngrok\ngrok.exe` - ngrok binary
- `start_telegram_with_ngrok.bat` - Automated startup script
- `setup_webhook_url.py` - Webhook configuration script
- `TELEGRAM_QUICK_START.md` - Quick reference guide
- `TELEGRAM_SETUP_COMPLETE.md` - This file

## 🎯 Next Steps

1. Run `start_telegram_with_ngrok.bat`
2. Wait for all services to start (about 10 seconds)
3. Send a test trade to your Telegram bot
4. Check the webhook server window for incoming messages
5. Verify you receive a confirmation reply from the bot

## ❓ Need Help?

If messages still aren't coming through:
1. Check that all three services are running (webhook server, ngrok, webhook configured)
2. Look at the ngrok window - verify you have a public HTTPS URL
3. Check the webhook server window - should show incoming POST requests
4. Verify your bot token is correct in the `.env.dev` file
5. Try sending a simple message first, then the trade command

---

**You're all set! Run the batch file and start trading via Telegram!** 🚀

