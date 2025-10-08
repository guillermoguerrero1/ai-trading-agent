#!/usr/bin/env python3
"""
Setup script for Telegram webhook with ngrok
This script helps you set up the webhook URL for your Telegram bot
"""

import os
import subprocess
import time
import requests
import json
from pathlib import Path

def check_ngrok():
    """Check if ngrok is installed and running."""
    try:
        result = subprocess.run(["ngrok", "version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"ngrok is installed: {result.stdout.strip()}")
            return True
        else:
            print("ngrok is not installed or not in PATH")
            return False
    except FileNotFoundError:
        print("ngrok is not installed or not in PATH")
        return False

def start_ngrok(port=8000):
    """Start ngrok tunnel."""
    print(f"Starting ngrok tunnel on port {port}...")
    
    try:
        # Start ngrok in background
        process = subprocess.Popen(
            ["ngrok", "http", str(port), "--log=stdout"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait a moment for ngrok to start
        time.sleep(3)
        
        # Get ngrok public URL
        try:
            response = requests.get("http://localhost:4040/api/tunnels", timeout=5)
            if response.status_code == 200:
                tunnels = response.json()
                if tunnels.get("tunnels"):
                    public_url = tunnels["tunnels"][0]["public_url"]
                    print(f"ngrok tunnel started: {public_url}")
                    return public_url, process
                else:
                    print("No tunnels found")
                    return None, process
            else:
                print("Failed to get ngrok tunnel info")
                return None, process
        except Exception as e:
            print(f"Error getting ngrok URL: {e}")
            return None, process
            
    except Exception as e:
        print(f"Failed to start ngrok: {e}")
        return None, None

def set_telegram_webhook(bot_token, webhook_url):
    """Set the Telegram webhook URL."""
    url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
    data = {"url": webhook_url}
    
    print(f"Setting webhook URL: {webhook_url}")
    
    try:
        response = requests.post(url, json=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get("ok"):
                print("Webhook set successfully!")
                return True
            else:
                print(f"Failed to set webhook: {result.get('description', 'Unknown error')}")
                return False
        else:
            print(f"HTTP error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"Error setting webhook: {e}")
        return False

def get_webhook_info(bot_token):
    """Get current webhook info."""
    url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get("ok"):
                webhook_info = result.get("result", {})
                return webhook_info
            else:
                print(f"Failed to get webhook info: {result.get('description', 'Unknown error')}")
                return None
        else:
            print(f"HTTP error {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"Error getting webhook info: {e}")
        return None

def main():
    """Main setup function."""
    print("Telegram Webhook Setup Script")
    print("=" * 40)
    
    # Check ngrok
    if not check_ngrok():
        print("\nTo install ngrok:")
        print("1. Download from: https://ngrok.com/download")
        print("2. Extract and add to PATH")
        print("3. Run this script again")
        return
    
    # Get bot token
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "8443339641:AAEODDBahaHiNI5id_Np3yqyBmVinTqha9c")
    if not bot_token:
        print("Please set TELEGRAM_BOT_TOKEN environment variable")
        return
    
    print(f"Using bot token: {bot_token[:10]}...")
    
    # Start ngrok
    public_url, ngrok_process = start_ngrok(8000)
    if not public_url:
        print("Failed to start ngrok tunnel")
        return
    
    webhook_url = f"{public_url}/webhook"
    print(f"Webhook URL: {webhook_url}")
    
    # Set webhook
    if set_telegram_webhook(bot_token, webhook_url):
        print("\nSetup complete!")
        print(f"Send messages to your bot to test")
        print(f"Webhook URL: {webhook_url}")
        print("\nTest commands:")
        print("   trade NQZ5 buy 1 @ 17895 stop 17885 target 17915")
        print("   NQZ5 sell 2 @ 20450 stop 20460 target 20430")
        
        # Keep ngrok running
        print(f"\nngrok tunnel is running... Press Ctrl+C to stop")
        try:
            ngrok_process.wait()
        except KeyboardInterrupt:
            print("\nStopping ngrok tunnel...")
            ngrok_process.terminate()
            ngrok_process.wait()
            
            # Clear webhook
            print("Clearing webhook...")
            set_telegram_webhook(bot_token, "")
            print("Setup cleaned up!")
    else:
        print("Failed to set webhook")
        if ngrok_process:
            ngrok_process.terminate()

if __name__ == "__main__":
    main()
