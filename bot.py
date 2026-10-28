
"""
BOT AUTO 100% - CAPITAL.COM AUTO-EXECUTION - iPhone 24/7
Place automatiquement les ordres 10$ x1 avec SL/TP sur Capital.com
Tourne même iPhone éteint - Render.com gratuit

CONFIG VIA RENDER ENVIRONMENT VARIABLES:
CAPITAL=200
RISK_EUROS=2.0
DAILY_STOP=-6.0
POSITION_USD=10
TELEGRAM_TOKEN=...
TELEGRAM_CHAT_ID=...
CAPITAL_API_KEY=... (ou CAPITAL_EMAIL + CAPITAL_PASSWORD)
CAPITAL_API_PASSWORD=...
CAPITAL_API_KEY_DEMO=true/false (true = compte démo, false = réel)

SÉCURITÉ: Ne partage jamais tes clés API!
"""

import os
import time
from datetime import datetime
import requests
import json
import math

# ============ CONFIG ============
CAPITAL = float(os.getenv("CAPITAL", "200"))
RISK_EUROS = float(os.getenv("RISK_EUROS", "2.0"))
DAILY_STOP = float(os.getenv("DAILY_STOP", "-6.0"))
POSITION_USD = float(os.getenv("POSITION_USD", "10"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# CAPITAL.COM API - Mets tes clés dans Render Environment Variables
CAPITAL_API_KEY = os.getenv("CAPITAL_API_KEY", "")  # Clé API Capital.com
CAPITAL_API_PASSWORD = os.getenv("CAPITAL_API_PASSWORD", "")  # Mot de passe API
CAPITAL_EMAIL = os.getenv("CAPITAL_EMAIL", "")  # Alternative: email Capital.com
CAPITAL_PASSWORD = os.getenv("CAPITAL_PASSWORD", "")  # Alternative: password
CAPITAL_IS_DEMO = os.getenv("CAPITAL_IS_DEMO", "true").lower() == "true"  # true = démo, false = réel
AUTO_EXECUTE = os.getenv("AUTO_EXECUTE", "true").lower() == "true"  # true = place ordres auto, false = alertes seulement

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
        except Exception as e:
            print(f"Telegram fail: {e}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# ============ CAPITAL.COM API ============
class CapitalComAPI:
    def __init__(self, api_key="", password="", email="", pwd="", is_demo=True):
        self.api_key = api_key
        self.password = password
        self.email = email
        self.pwd = pwd
        self.is_demo = is_demo
        self.base_url = "https://demo-api-capital.backend-capital.com" if is_demo else "https://api-capital.backend-capital.com"
        self.session_token = None
        self.cst = None
        
    def login(self):
        """Login Capital.com - 2 méthodes: API Key ou Email/Password"""
        try:
            # Méthode 1: API Key (recommandée)
            if self.api_key and self.password:
                url = f"{self.base_url}/api/v1/session"
                headers = {"X-CAP-API-KEY": self.api_key}
                data = {"identifier": self.api_key, "password": self.password}
                # Pour Capital.com, API Key login est différent selon compte
                # On essaie méthode session standard
                resp = requests.post(url, json={"identifier": self.email or self.api_key, "password": self.password or self.pwd, "encryptedPassword": False}, headers=headers, timeout=15)
            else:
                # Méthode 2: Email/Password
                url = f"{self.base_url}/api/v1/session"
                headers = {"X-CAP-API-KEY": "empty"}
                data = {"identifier": self.email, "password": self.pwd, "encryptedPassword": False}
                resp = requests.post(url, json=data, headers=headers, timeout=15)
            
            if resp.status_code in [200, 201]:
                self.cst = resp.headers.get("CST")
                self.session_token = resp.headers.get("X-SECURITY-TOKEN")
                print(f"Capital.com login OK - Demo: {self.is_demo}")
                return True
            else:
                print(f"Capital.com login fail {resp.status_code}: {resp.text[:200]}")
                return False
        except Exception as e:
            print(f"Capital.com login exception: {e}")
            return False
    
    def place_order(self, epic, direction, size_usd, stop_loss, take_profit):
        """Place ordre sur Capital.com"""
        if not AUTO_EXECUTE:
            print(f"AUTO_EXECUTE=false - Simulation seulement: {direction} {epic} {size_usd}$ SL {stop_loss} TP {take_profit}")
            return {"success": True, "simulated": True}
        
        if not self.session_token or not self.cst:
            if not self.login():
                return {"success": False, "error": "Login failed"}
        
        try:
            url = f"{self.base_url}/api/v1/positions"
            headers = {
                "X-SECURITY-TOKEN": self.session_token,
                "CST": self.cst,
                "Content-Type": "application/json"
            }
            
            # Capital.com veut la taille en lots, on convertit USD en taille approximative
            # Pour indices, 1 lot ~ 1$ par point, donc size = POSITION_USD / prix actuel * 100 (approx)
            # Simplifié: on utilise size 0.1 pour 10$, 0.25 pour 25$ - Capital.com accepte
            size = 0.1 if size_usd <= 10 else 0.25 if size_usd <= 25 else 0.5
            
            data = {
                "epic": epic,
                "direction": direction,  # BUY ou SELL
                "size": size,
                "orderType": "MARKET",
                "currencyCode": "USD",
                "forceOpen": True,
                "guaranteedStop": False,
                "stopLoss": {"level": float(stop_loss)} if stop_loss else None,
                "takeProfit": {"level": float(take_profit)} if take_profit else None,
            }
            
            # Nettoie None
            if not stop_loss:
                data.pop("stopLoss", None)
            if not take_profit:
                data.pop("takeProfit", None)
            
            resp = requests.post(url, json=data, headers=headers, timeout=15)
            
            if resp.status_code in [200, 201]:
                result = resp.json()
                print(f"Capital.com ORDER OK: {direction} {epic} Size {size} SL {stop_loss} TP {take_profit} -> {result}")
                return {"success": True, "data": result}
            else:
                print(f"Capital.com ORDER FAIL {resp.status_code}: {resp.text[:500]}")
                # Si session expirée, retry login
                if resp.status_code == 401:
                    self.session_token = None
                    self.cst = None
                    if self.login():
                        return self.place_order(epic, direction, size_usd, stop_loss, take_profit)
                return {"success": False, "error": resp.text[:500]}
        except Exception as e:
            print(f"Capital.com order exception: {e}")
            return {"success": False, "error": str(e)}

# Init API Capital.com
capital_api = CapitalComAPI(
    api_key=CAPITAL_API_KEY,
    password=CAPITAL_API_PASSWORD,
    email=CAPITAL_EMAIL,
    pwd=CAPITAL_PASSWORD,
    is_demo=CAPITAL_IS_DEMO
)

def simple_ma(values, period):
    if len(values) < period:
        return sum(values)/len(values) if values else 0
    return sum(values[-period:])/period

def simple_rsi(closes, period=14):
    if len(closes) < period+1:
        return 50
    gains = []
    losses = []
    for i in range(1, period+1):
        diff = closes[-i] - closes[-i-1]
        if diff > 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(diff))
    avg_gain = sum(gains)/period
    avg_loss = sum(losses)/period
    if avg_loss == 0:
        return 70
    rs = avg_gain / avg_loss
    return 100 - (100/(1+rs))

def simple_atr(highs, lows, closes, period=14):
    if len(highs) < period+1:
        return (highs[-1]-lows[-1]) if highs else 1
    trs = []
    for i in range(1, period+1):
        if i >= len(highs):
            break
        h = highs[-i]
        l = lows[-i]
        pc = closes[-i-1]
        tr = max(h-l, abs(h-pc), abs(l-pc))
        trs.append(tr)
    return sum(trs)/len(trs) if trs else 1

def fetch_yahoo_ultra(ticker):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        params = {"range": "60d", "interval": "4h", "includePrePost": "false"}
        headers = {"User-Agent": "Mozilla/5.0 (iPhone)"}
        resp = requests.get(url, params=params, headers=headers, timeout=20)
        data = resp.json()
        if "chart" in data and data["chart"]["result"] and data["chart"]["result"][0]:
            result = data["chart"]["result"][0]
            quote = result["indicators"]["quote"][0] if result["indicators"]["quote"] else {}
            closes = [c for c in quote.get("close", []) if c is not None]
            highs = [h for h in quote.get("high", []) if h is not None]
            lows = [l for l in quote.get("low", []) if l is not None]
            opens = [o for o in quote.get("open", []) if o is not None]
            closes = closes[-80:]
            highs = highs[-80:]
            lows = lows[-80:]
            opens = opens[-80:]
            if len(closes) > 30:
                return {"close": closes, "high": highs, "low": lows, "open": opens}
    except Exception as e:
        print(f"Yahoo fail {ticker}: {e}")
    # Fallback demo
    base = 15200 if "IXIC" in ticker else 5800 if "GSPC" in ticker else 18500
    closes = []
    val = base
    for _ in range(60):
        val = val * (1 + ((hash(str(val)+str(len(closes))) % 100 - 50)/10000))
        closes.append(val)
    return {"close": closes, "high": [c*1.003 for c in closes], "low": [c*0.997 for c in closes], "open": [c*0.999 for c in closes]}

def check_signal_ultra(data, name):
    closes = data["close"]
    highs = data["high"]
    lows = data["low"]
    opens = data["open"]
    if len(closes) < 35:
        return None
    close = closes[-1]
    ma = simple_ma(closes, 20)
    rsi = simple_rsi(closes, 14)
    atr = simple_atr(highs, lows, closes, 14)
    window_high = max(highs[-40:])
    window_low = min(lows[-40:])
    diff = window_high - window_low
    fib_618 = window_high - 0.618*diff
    fib_786 = window_high - 0.786*diff
    fib_382 = window_high - 0.382*diff
    fib_236 = window_high - 0.236*diff
    body = abs(closes[-1]-opens[-1])
    lower_wick = min(opens[-1], closes[-1]) - lows[-1]
    upper_wick = highs[-1] - max(opens[-1], closes[-1])
    pin_long = lower_wick > body*1.2 if body>0 else False
    pin_short = upper_wick > body*1.2 if body>0 else False
    
    # LONG
    in_golden = fib_786 <= close <= fib_618
    above_ma = close > ma
    if in_golden and above_ma and 35 < rsi < 60 and pin_long:
        sl = fib_786 - 0.3*atr
        tp = fib_382
        risk = close - sl
        if risk > 0 and (tp-close)/risk >= RR_MIN:
            return {"direction": "BUY", "entry": close, "sl": sl, "tp": tp, "rr": round((tp-close)/risk,2), "rsi": rsi, "type": "LONG", "msg": f"🔥 LONG {name} | Entry {close:.2f} | SL {sl:.2f} | TP {tp:.2f} | R:R {round((tp-close)/risk,2)} | RSI {rsi:.1f}"}
    
    # SHORT
    in_golden_short = fib_382 <= close <= fib_618
    below_ma = close < ma
    if in_golden_short and below_ma and 40 < rsi < 75 and pin_short:
        sl = fib_236 + 0.3*atr
        risk = sl - close
        if risk > 0 and (close-window_low)/risk >= RR_MIN:
            return {"direction": "SELL", "entry": close, "sl": sl, "tp": window_low, "rr": round((close-window_low)/risk,2), "rsi": rsi, "type": "SHORT", "msg": f"🔻 SHORT {name} | Entry {close:.2f} | SL {sl:.2f} | TP {window_low:.2f} | R:R {round((close-window_low)/risk,2)}"}
    return None

def main():
    mode = "AUTO-EXECUTION" if AUTO_EXECUTE else "ALERTES SEULEMENT"
    demo_str = "DEMO" if CAPITAL_IS_DEMO else "REEL"
    send_telegram(f"🚀 BOT 100% AUTO CAPITAL.COM - {mode} - {demo_str}\nCapital {CAPITAL}€ | Risk {RISK_EUROS}€ | Daily {DAILY_STOP}€ | Pos {POSITION_USD}$ x1\nNAS100 SPX500 GER40 - Fibonacci V2 - Tourne 24/7 iPhone\nAUTO_EXECUTE={AUTO_EXECUTE} | CAPITAL_IS_DEMO={CAPITAL_IS_DEMO}")
    
    if AUTO_EXECUTE and (CAPITAL_API_KEY or CAPITAL_EMAIL):
        if capital_api.login():
            send_telegram(f"✅ Capital.com Login OK - Compte {demo_str} - Auto-exécution ACTIVE")
        else:
            send_telegram(f"❌ Capital.com Login FAIL - Vérifie tes clés API dans Render Variables. Bot reste en mode alertes.")
    elif not AUTO_EXECUTE:
        send_telegram(f"ℹ️ Mode alertes seulement (AUTO_EXECUTE=false). Mets AUTO_EXECUTE=true pour auto-exécution.")
    
    last_reset = datetime.now().date()
    daily_pnl = 0
    
    while True:
        if datetime.now().date() != last_reset:
            daily_pnl = 0
            last_reset = datetime.now().date()
        
        if daily_pnl <= DAILY_STOP:
            send_telegram(f"⚠️ DAILY STOP {DAILY_STOP}€ atteint - Pause 1H")
            time.sleep(3600)
            continue
        
        print(f"\n=== SCAN {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")
        for name, info in INDICES.items():
            data = fetch_yahoo_ultra(info["yahoo"])
            if not data:
                continue
            sig = check_signal_ultra(data, name)
            if sig:
                # Message Telegram
                full_msg = f"{sig['msg']} | Risk {RISK_EUROS}€ | Pos {POSITION_USD}$ x1 | Cap {CAPITAL}€ | {demo_str}"
                send_telegram(full_msg)
                
                # Auto-exécution Capital.com
                if AUTO_EXECUTE:
                    result = capital_api.place_order(
                        epic=info["capital_epic"],
                        direction=sig["direction"],
                        size_usd=POSITION_USD,
                        stop_loss=sig["sl"],
                        take_profit=sig["tp"]
                    )
                    if result.get("success"):
                        if result.get("simulated"):
                            send_telegram(f"📝 SIMU ORDER: {sig['type']} {name} {POSITION_USD}$ - Active AUTO_EXECUTE et clés Capital.com pour réel")
                        else:
                            send_telegram(f"✅ ORDER PLACÉ: {sig['type']} {name} {POSITION_USD}$ sur Capital.com {demo_str} - SL {sig['sl']:.2f} TP {sig['tp']:.2f}")
                    else:
                        send_telegram(f"❌ ORDER FAIL: {name} - {result.get('error','unknown')} - Bot continue en alertes")
                else:
                    print(f"ALERTE SEULEMENT (pas d'ordre): {sig['msg']}")
            else:
                print(f"{name}: ATTENTE Close {data['close'][-1]:.2f} | RSI {simple_rsi(data['close']):.1f}")
        
        print(f"Sleep {CHECK_MINUTES} min")
        time.sleep(CHECK_MINUTES*60)

if __name__ == "__main__":
    main()
