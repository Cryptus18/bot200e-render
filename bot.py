

import os
import time
from datetime import datetime
import requests

print("=== BOT MINIMAL START ===", flush=True)
print(f"Time: {datetime.now()}", flush=True)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

print(f"TOKEN set: {bool(TELEGRAM_TOKEN)} len={len(TELEGRAM_TOKEN) if TELEGRAM_TOKEN else 0}", flush=True)
print(f"CHAT_ID set: {bool(TELEGRAM_CHAT_ID)} value={TELEGRAM_CHAT_ID}", flush=True)

def send_telegram(msg):
    print(f"Attempting Telegram: {msg[:50]}...", flush=True)
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("SKIP Telegram - token or chat_id empty", flush=True)
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
        print(f"POST {url[:60]}... chat_id={TELEGRAM_CHAT_ID}", flush=True)
        resp = requests.post(url, data=data, timeout=15)
        print(f"Telegram response: {resp.status_code} - {resp.text[:500]}", flush=True)
        return resp.status_code == 200
    except Exception as e:
        print(f"Telegram exception: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return False

# Test immédiat
print("Sending test message...", flush=True)
ok = send_telegram(f"🚀 TEST MINIMAL - Bot demarre - {datetime.now().strftime('%H:%M:%S')} - Capital {os.getenv('CAPITAL','200')}€")

if not ok:
    print("TELEGRAM FAILED - Check token/chat_id", flush=True)
else:
    print("TELEGRAM OK", flush=True)

counter = 0
while True:
    counter += 1
    print(f"Loop #{counter} - {datetime.now().strftime('%H:%M:%S')} - Alive", flush=True)
    send_telegram(f"✅ Loop #{counter} - Bot vivant - {datetime.now().strftime('%H:%M:%S')} - Test minimal")
    print("Sleep 60s...", flush=True)
    time.sleep(60)
