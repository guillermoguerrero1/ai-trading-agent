@echo off
echo Starting Telegram Webhook Server with ngrok
echo ============================================

echo.
echo Step 1: Starting webhook server...
start "Webhook Server" cmd /k "cd /d %~dp0 && python telegram_webhook_server.py"
timeout /t 3 /nobreak

echo Step 2: Starting ngrok tunnel...
start "ngrok" cmd /k "C:\Users\Owner\ngrok\ngrok.exe http 8000"
timeout /t 8 /nobreak

echo Step 3: Setting up webhook URL...
python setup_webhook_url.py

echo.
echo ============================================
echo Check the windows that opened above!
echo - Webhook Server window should show server running
echo - ngrok window should show the public URL
echo.
echo If everything is running, test by sending a message to your bot:
echo   trade NQZ5 buy 1 @ 17895 stop 17885 target 17915
echo.

