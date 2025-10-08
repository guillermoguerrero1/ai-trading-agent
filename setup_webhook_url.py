#!/usr/bin/env python3
"""
Get ngrok URL and set up Telegram webhook
"""

import requests
import json
import time

def get_ngrok_url():
    """Get the public ngrok URL."""
    try:
        response = requests.get("http://localhost:4040/api/tunnels", timeout=5)
        if response.status_code == 200:
            tunnels = response.json()
            if tunnels.get("tunnels"):
                # Get the HTTPS URL
                for tunnel in tunnels["tunnels"]:
                    if tunnel.get("proto") == "https":
                        return tunnel.get("public_url")
                # Fallback to first tunnel
                return tunnels["tunnels"][0].get("public_url")
            else:
                print("No ngrok tunnels found")
                return None
        else:
            print(f"Error getting ngrok tunnels: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error connecting to ngrok API: {e}")
        return None

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
                return result.get("result", {})
        return None
    except Exception as e:
        print(f"Error getting webhook info: {e}")
        return None

def main():
    bot_token = "8443339641:AAEODDBahaHiNI5id_Np3yqyBmVinTqha9c"
    
    print("Telegram Webhook Setup")
    print("=" * 40)
    
    # Get ngrok URL
    print("Getting ngrok URL...")
    ngrok_url = get_ngrok_url()
    
    if not ngrok_url:
        print("Failed to get ngrok URL. Make sure ngrok is running.")
        print("Start ngrok with: C:\\Users\\Owner\\ngrok\\ngrok.exe http 8000")
        return
    
    print(f"ngrok URL: {ngrok_url}")
    
    # Set webhook URL
    webhook_url = f"{ngrok_url}/webhook"
    success = set_telegram_webhook(bot_token, webhook_url)
    
    if success:
        print("\nWebhook setup complete!")
        print(f"Webhook URL: {webhook_url}")
        print("\nYou can now send messages to your Telegram bot!")
        print("Try sending: trade NQZ5 buy 1 @ 17895 stop 17885 target 17915")
        
        # Show webhook info
        print("\nWebhook Status:")
        webhook_info = get_webhook_info(bot_token)
        if webhook_info:
            print(f"  URL: {webhook_info.get('url')}")
            print(f"  Pending updates: {webhook_info.get('pending_update_count', 0)}")
    else:
        print("\nFailed to set up webhook.")

if __name__ == "__main__":
    main()

