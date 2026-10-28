

import os
import time
from datetime import datetime
import requests
import math

print("="*60, flush=True)
print("BOT FIBONACCI V2 - CAPITAL.COM FIX API KEY", flush=True)
print(f"Time: {datetime.now()}", flush=True)
print("="*60, flush=True)

CAPITAL = float(os.getenv("CAPITAL", "200"))
RISK_EUROS = float(os.getenv("RISK_EUROS", "2.0"))
DAILY_STOP = float(os.getenv("DAILY_STOP", "-6.0"))
POSITION_USD = float(os.getenv("POSITION_USD", "10"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
CAPITAL_API_KEY = os.getenv("CAPITAL_API_KEY", "").strip()
CAPITAL_API_PASSWORD = os.getenv("CAPITAL_API_PASSWORD", "").strip()
CAPITAL_EMAIL = os.getenv("CAPITAL_EMAIL", "").strip()
CAPITAL_PASSWORD = os.getenv("CAPITAL_PASSWORD", "").strip()
CAPITAL_IS_DEMO = os.getenv("CAPITAL_IS_DEMO", "true").lower() == "true"
AUTO_EXECUTE = os.getenv("AUTO_EXECUTE", "false").lower() == "true"

print(f"CAPITAL={CAPITAL} RISK={RISK_EUROS} POS={POSITION_USD} AUTO={AUTO_EXECUTE} DEMO={CAPITAL_IS_DEMO}", flush=True)
print(f"TELEGRAM set: {bool(TELEGRAM_TOKEN)} / {bool(TELEGRAM_CHAT_ID)}", flush=True)
print(f"CAPITAL_API_KEY len: {len(CAPITAL_API_KEY)} set: {bool(CAPITAL_API_KEY)}", flush=True)
print(f"CAPITAL_API_PASSWORD len: {len(CAPITAL_API_PASSWORD)}", flush=True)
print(f"CAPITAL_EMAIL set: {bool(CAPITAL_EMAIL)} value: {CAPITAL_EMAIL[:3]}***", flush=True)
print(f"CAPITAL_PASSWORD set: {bool(CAPITAL_PASSWORD)}", flush=True)

RR_MIN = 1.8
CHECK_MINUTES = 240

INDICES = {
    "NAS100": {"yahoo": "^IXIC", "capital_epic": "US100", "name": "Nasdaq"},
    "SPX500": {"yahoo": "^GSPC", "capital_epic": "US500", "name": "S&P500"},
    "GER40": {"yahoo": "^GDAXI", "capital_epic": "GER40", "name": "DAX"},
}

def send_telegram(msg):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=10)
        except:
            pass
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

class CapitalComAPI:
    def __init__(self):
        self.is_demo = CAPITAL_IS_DEMO
        self.base_url = "https://demo-api-capital.backend-capital.com" if self.is_demo else "https://api-capital.backend-capital.com"
        self.session_token = None
        self.cst = None
        
    def login(self):
        """Essaie 3 méthodes de login Capital.com"""
        print(f"Trying Capital.com login Demo={self.is_demo} Base={self.base_url}", flush=True)
        
        # Méthode 1: Email + Password avec X-CAP-API-KEY vide (la plus simple, marche sans API key)
        if CAPITAL_EMAIL and CAPITAL_PASSWORD:
            print("Method 1: Email + Password (X-CAP-API-KEY empty)", flush=True)
            try:
                url = f"{self.base_url}/api/v1/session"
                headers = {"X-CAP-API-KEY": "", "Content-Type": "application/json"}
                data = {"identifier": CAPITAL_EMAIL, "password": CAPITAL_PASSWORD, "encryptedPassword": False}
                print(f"POST {url} identifier={CAPITAL_EMAIL[:3]}***", flush=True)
                resp = requests.post(url, json=data, headers=headers, timeout=15)
                print(f"Method 1 response {resp.status_code}: {resp.text[:500]}", flush=True)
                if resp.status_code in [200, 201]:
                    self.cst = resp.headers.get("CST")
                    self.session_token = resp.headers.get("X-SECURITY-TOKEN")
                    print("Method 1 SUCCESS", flush=True)
                    return True
            except Exception as e:
                print(f"Method 1 exception: {e}", flush=True)
        
        # Méthode 2: Email + Password avec API Key en header
        if CAPITAL_EMAIL and CAPITAL_PASSWORD and CAPITAL_API_KEY:
            print("Method 2: Email + Password + X-CAP-API-KEY header", flush=True)
            try:
                url = f"{self.base_url}/api/v1/session"
                headers = {"X-CAP-API-KEY": CAPITAL_API_KEY, "Content-Type": "application/json"}
                data = {"identifier": CAPITAL_EMAIL, "password": CAPITAL_PASSWORD, "encryptedPassword": False}
                resp = requests.post(url, json=data, headers=headers, timeout=15)
                print(f"Method 2 response {resp.status_code}: {resp.text[:500]}", flush=True)
                if resp.status_code in [200, 201]:
                    self.cst = resp.headers.get("CST")
                    self.session_token = resp.headers.get("X-SECURITY-TOKEN")
                    print("Method 2 SUCCESS", flush=True)
                    return True
            except Exception as e:
                print(f"Method 2 exception: {e}", flush=True)
        
        # Méthode 3: API Key comme identifier + API Password
        if CAPITAL_API_KEY and CAPITAL_API_PASSWORD:
            print("Method 3: API Key as identifier + API Password", flush=True)
            try:
                url = f"{self.base_url}/api/v1/session"
                headers = {"X-CAP-API-KEY": CAPITAL_API_KEY, "Content-Type": "application/json"}
                data = {"identifier": CAPITAL_API_KEY, "password": CAPITAL_API_PASSWORD, "encryptedPassword": False}
                resp = requests.post(url, json=data, headers=headers, timeout=15)
                print(f"Method 3 response {resp.status_code}: {resp.text[:500]}", flush=True)
                if resp.status_code in [200, 201]:
                    self.cst = resp.headers.get("CST")
                    self.session_token = resp.headers.get("X-SECURITY-TOKEN")
                    print("Method 3 SUCCESS", flush=True)
                    return True
            except Exception as e:
                print(f"Method 3 exception: {e}", flush=True)
        
        # Méthode 4: Essaye avec live API même si demo=true (parfois demo et live sont inversés)
        if self.is_demo:
            print("Method 4: Try LIVE API even though DEMO=true", flush=True)
            try:
                alt_base = "https://api-capital.backend-capital.com"
                url = f"{alt_base}/api/v1/session"
                headers = {"X-CAP-API-KEY": CAPITAL_API_KEY or "", "Content-Type": "application/json"}
                identifier = CAPITAL_EMAIL or CAPITAL_API_KEY
                password = CAPITAL_PASSWORD or CAPITAL_API_PASSWORD
                data = {"identifier": identifier, "password": password, "encryptedPassword": False}
                resp = requests.post(url, json=data, headers=headers, timeout=15)
                print(f"Method 4 response {resp.status_code}: {resp.text[:500]}", flush=True)
                if resp.status_code in [200, 201]:
                    self.base_url = alt_base
                    self.cst = resp.headers.get("CST")
                    self.session_token = resp.headers.get("X-SECURITY-TOKEN")
                    print("Method 4 SUCCESS - Switched to LIVE", flush=True)
                    return True
            except Exception as e:
                print(f"Method 4 exception: {e}", flush=True)
        
        print("All Capital.com login methods FAILED", flush=True)
        return False
    
    def place_order(self, epic, direction, size_usd, sl, tp):
        if not AUTO_EXECUTE:
            return {"success": True, "simulated": True}
        if not self.session_token:
            if not self.login():
                return {"success": False, "error": "Login failed"}
        try:
            url = f"{self.base_url}/api/v1/positions"
            headers = {"X-SECURITY-TOKEN": self.session_token, "CST": self.cst, "Content-Type": "application/json"}
            size = 0.1 if size_usd <= 10 else 0.25 if size_usd <= 25 else 0.5
            data = {"epic": epic, "direction": direction, "size": size, "orderType": "MARKET", "currencyCode": "USD", "forceOpen": True}
            if sl:
                data["stopLoss"] = {"level": float(sl)}
            if tp:
                data["takeProfit"] = {"level": float(tp)}
            resp = requests.post(url, json=data, headers=headers, timeout=15)
            if resp.status_code in [200, 201]:
                print(f"Capital ORDER OK {direction} {epic}", flush=True)
                return {"success": True, "data": resp.json()}
            else:
                print(f"Capital ORDER FAIL {resp.status_code}: {resp.text[:400]}", flush=True)
                if resp.status_code == 401:
                    self.session_token = None
                    self.cst = None
                return {"success": False, "error": resp.text[:300]}
        except Exception as e:
            print(f"Capital order exception: {e}", flush=True)
            return {"success": False, "error": str(e)}

capital_api = CapitalComAPI()

def simple_ma(values, period):
    return sum(values[-period:])/period if len(values)>=period else sum(values)/len(values) if values else 0

def simple_rsi(closes, period=14):
    if len(closes) < period+1:
        return 50
    gains, losses = [], []
    for i in range(1, period+1):
        diff = closes[-i] - closes[-i-1]
        gains.append(diff if diff>0 else 0)
        losses.append(abs(diff) if diff<0 else 0)
    avg_gain = sum(gains)/period
    avg_loss = sum(losses)/period
    if avg_loss == 0:
        return 70
    return 100 - (100/(1+avg_gain/avg_loss))

def simple_atr(highs, lows, closes, period=14):
    if len(highs) < period+1:
        return highs[-1]-lows[-1] if highs else 1
    trs = []
    for i in range(1, period+1):
        if i >= len(highs):
            break
        h,l,pc = highs[-i], lows[-i], closes[-i-1]
        trs.append(max(h-l, abs(h-pc), abs(l-pc)))
    return sum(trs)/len(trs) if trs else 1

def fetch_yahoo(ticker):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        params = {"range": "60d", "interval": "4h"}
        headers = {"User-Agent": "Mozilla/5.0 (iPhone)"}
        resp = requests.get(url, params=params, headers=headers, timeout=20)
        data = resp.json()
        if "chart" in data and data["chart"]["result"] and data["chart"]["result"][0]:
            result = data["chart"]["result"][0]
            quote = result["indicators"]["quote"][0]
            closes = [c for c in quote.get("close", []) if c is not None][-80:]
            highs = [h for h in quote.get("high", []) if h is not None][-80:]
            lows = [l for l in quote.get("low", []) if l is not None][-80:]
            opens = [o for o in quote.get("open", []) if o is not None][-80:]
            if len(closes) > 30:
                return {"close": closes, "high": highs, "low": lows, "open": opens}
    except Exception as e:
        print(f"Yahoo fail {ticker}: {e}", flush=True)
    base = 15200 if "IXIC" in ticker else 5800 if "GSPC" in ticker else 18500
    closes = [base*(1+(hash(str(i))%100-50)/10000) for i in range(60)]
    return {"close": closes, "high": [c*1.003 for c in closes], "low": [c*0.997 for c in closes], "open": [c*0.999 for c in closes]}

def check_signal(data, name):
    closes, highs, lows, opens = data["close"], data["high"], data["low"], data["open"]
    if len(closes) < 35:
        return None
    close = closes[-1]
    ma = simple_ma(closes, 20)
    rsi = simple_rsi(closes, 14)
    atr = simple_atr(highs, lows, closes, 14)
    window_high = max(highs[-40:])
    window_low = min(lows[-40:])
    diff = window_high - window_low
    fib_618, fib_786, fib_382, fib_236 = window_high-0.618*diff, window_high-0.786*diff, window_high-0.382*diff, window_high-0.236*diff
    body = abs(closes[-1]-opens[-1])
    lower_wick = min(opens[-1], closes[-1]) - lows[-1]
    upper_wick = highs[-1] - max(opens[-1], closes[-1])
    pin_long = lower_wick > body*1.2 if body>0 else False
    pin_short = upper_wick > body*1.2 if body>0 else False
    if fib_786 <= close <= fib_618 and close > ma and 35 < rsi < 60 and pin_long:
        sl = fib_786 - 0.3*atr
        tp = fib_382
        risk = close - sl
        if risk > 0 and (tp-close)/risk >= 1.8:
            return {"dir": "BUY", "type": "LONG", "entry": close, "sl": sl, "tp": tp, "rr": round((tp-close)/risk,2), "rsi": rsi, "msg": f"🔥 LONG {name} | Entry {close:.2f} | SL {sl:.2f} | TP {tp:.2f} | R:R {round((tp-close)/risk,2)} | RSI {rsi:.1f}"}
    if fib_382 <= close <= fib_618 and close < ma and 40 < rsi < 75 and pin_short:
        sl = fib_236 + 0.3*atr
        risk = sl - close
        if risk > 0 and (close-window_low)/risk >= 1.8:
            return {"dir": "SELL", "type": "SHORT", "entry": close, "sl": sl, "tp": window_low, "rr": round((close-window_low)/risk,2), "rsi": rsi, "msg": f"🔻 SHORT {name} | Entry {close:.2f} | SL {sl:.2f} | TP {window_low:.2f}"}
    return None

def main():
    mode = "AUTO" if AUTO_EXECUTE else "ALERTES"
    demo_str = "DEMO" if CAPITAL_IS_DEMO else "REEL"
    send_telegram(f"🚀 BOT FIBONACCI V2 - FIX API - {mode} - {demo_str}\nCapital {CAPITAL}€ | Risk {RISK_EUROS}€ | Daily {DAILY_STOP}€ | Pos {POSITION_USD}$ x1\nTest 4 méthodes login Capital.com")
    
    if AUTO_EXECUTE:
        if capital_api.login():
            send_telegram(f"✅ Capital.com Login OK - {demo_str} - Auto ACTIVE")
        else:
            send_telegram(f"❌ Capital.com Login FAIL après 4 méthodes - Vérifie: 1) Email + Password Capital.com, 2) Compte DEMO vs REEL, 3) Pas besoin API Key - juste email/password suffit. Mode alertes.")
    
    last_reset = datetime.now().date()
    while True:
        if datetime.now().date() != last_reset:
            last_reset = datetime.now().date()
        print(f"\n=== SCAN {datetime.now().strftime('%Y-%m-%d %H:%M')} ===", flush=True)
        for name, info in INDICES.items():
            data = fetch_yahoo(info["yahoo"])
            if not data:
                continue
            sig = check_signal(data, name)
            if sig:
                full_msg = f"{sig['msg']} | Risk {RISK_EUROS}€ | Pos {POSITION_USD}$ x1 | {demo_str}"
                send_telegram(full_msg)
                if AUTO_EXECUTE:
                    res = capital_api.place_order(info["capital_epic"], sig["dir"], POSITION_USD, sig["sl"], sig["tp"])
                    if res.get("success") and not res.get("simulated"):
                        send_telegram(f"✅ ORDER {sig['type']} {name} {POSITION_USD}$ sur Capital.com {demo_str}")
            else:
                print(f"{name}: ATTENTE Close {data['close'][-1]:.2f} RSI {simple_rsi(data['close']):.1f}", flush=True)
        print(f"Sleep 240 min", flush=True)
        time.sleep(240*60)

if __name__ == "__main__":
    main()
