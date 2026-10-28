
"""
BOT RAILWAY 24/7 - iPhone - Solution B
Tourne 24/7 même iPhone éteint - Gratuit Railway.app
Capital: 200€ (change via variables Railway) | Risk 2€ | Daily Stop -6€
"""

import os
import time
import pandas as pd
import numpy as np
from datetime import datetime
import requests

# CONFIG VIA VARIABLES RAILWAY (ou par défaut 200€)
CAPITAL = float(os.getenv("CAPITAL", "200"))
RISK_EUROS = float(os.getenv("RISK_EUROS", "2.0"))
DAILY_STOP = float(os.getenv("DAILY_STOP", "-6.0"))
POSITION_USD = float(os.getenv("POSITION_USD", "10"))
MAX_POSITIONS = int(os.getenv("MAX_POSITIONS", "2"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

RR_MIN = 1.8
CHECK_MINUTES = 240  # 4H

INDICES = {
    "NAS100": {"yahoo": "^IXIC", "name": "Nasdaq +15.6% YTD BEST"},
    "SPX500": {"yahoo": "^GSPC", "name": "S&P500 +11.8% YTD"},
    "GER40": {"yahoo": "^GDAXI", "name": "DAX"},
}

def send_telegram(msg):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=10)
            print(f"[TG OK] {msg[:80]}...")
        except Exception as e:
            print(f"[TG FAIL] {e}")
    print(f"[{datetime.now().strftime('%H:%M')}] {msg}")

def fib_levels(high, low):
    d = high - low
    return {"61.8": high-0.618*d, "78.6": high-0.786*d, "38.2": high-0.382*d, "23.6": high-0.236*d, "100": low}

def check_signal(df, name):
    if len(df) < 60:
        return None
    last = df.iloc[-1]
    close, ma, rsi, atr = last['Close'], last['MA200'], last['RSI'], last['ATR']
    win = df.tail(50)
    high, low = win['High'].max(), win['Low'].min()
    fibs = fib_levels(high, low)
    
    body = abs(last['Close']-last['Open'])
    lower_wick = min(last['Open'], last['Close']) - last['Low']
    pin_long = lower_wick > body*1.2 if body>0 else False
    
    in_golden = fibs["78.6"] <= close <= fibs["61.8"]
    above_ma = close > ma
    rsi_ok = 35 < rsi < 55
    
    if in_golden and above_ma and rsi_ok and pin_long:
        sl = fibs["78.6"] - 0.3*atr
        tp = fibs["38.2"]
        risk = close - sl
        if risk>0 and (tp-close)/risk >= RR_MIN:
            return {"signal":"LONG","entry":close,"sl":sl,"tp":tp,"rr":round((tp-close)/risk,2),
                    "msg": f"🔥 LONG {name} | Entry {close:.2f} | SL {sl:.2f} | TP {tp:.2f} | R:R {round((tp-close)/risk,2)} | Risk {RISK_EUROS}€ | Pos {POSITION_USD}$ x1 | Cap {CAPITAL}€"}

    # SHORT
    upper_wick = last['High'] - max(last['Open'], last['Close'])
    pin_short = upper_wick > body*1.2 if body>0 else False
    in_golden_short = fibs["38.2"] <= close <= fibs["61.8"]
    below_ma = close < ma
    rsi_short_ok = 45 < rsi < 70
    if in_golden_short and below_ma and rsi_short_ok and pin_short:
        sl = fibs["23.6"] + 0.3*atr
        risk = sl - close
        if risk>0 and (close-fibs["100"])/risk >= RR_MIN:
            return {"signal":"SHORT","entry":close,"sl":sl,"tp":fibs["100"],"rr":round((close-fibs['100'])/risk,2),
                    "msg": f"🔻 SHORT {name} | Entry {close:.2f} | SL {sl:.2f} | TP {fibs['100']:.2f} | R:R {round((close-fibs['100'])/risk,2)}"}

    return None

def fetch_yahoo(yahoo_ticker):
    try:
        import yfinance as yf
        df = yf.download(yahoo_ticker, period="60d", interval="4h", progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if df.empty:
            return None
        df['MA200'] = df['Close'].rolling(50).mean().bfill()
        delta = df['Close'].diff()
        gain = delta.where(delta>0,0).rolling(14).mean()
        loss = -delta.where(delta<0,0).rolling(14).mean()
        rs = gain/loss
        df['RSI'] = 100 - (100/(1+rs))
        df['ATR'] = (df['High']-df['Low']).rolling(14).mean().bfill()
        df['RSI'] = df['RSI'].bfill()
        return df
    except Exception as e:
        print(f"Yahoo fail {yahoo_ticker}: {e}")
        return None

def main():
    send_telegram(f"🚀 BOT RAILWAY 24/7 DEMARRE - iPhone Solution B\nCapital {CAPITAL}€ | Risk {RISK_EUROS}€ | Daily Stop {DAILY_STOP}€ | Pos {POSITION_USD}$ x1\nScan NAS100 SPX500 GER40 toutes les 4H")
    daily_pnl = 0
    last_reset = datetime.now().date()
    
    while True:
        if datetime.now().date() != last_reset:
            daily_pnl = 0
            last_reset = datetime.now().date()
            send_telegram(f"📅 Nouveau jour {last_reset} - Daily PnL reset 0€")
        
        if daily_pnl <= DAILY_STOP:
            send_telegram(f"⚠️ DAILY STOP {DAILY_STOP}€ atteint! PnL: {daily_pnl}€ - Pause 1H")
            time.sleep(3600)
            continue
        
        print(f"\n=== SCAN {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")
        for name, info in INDICES.items():
            df = fetch_yahoo(info["yahoo"])
            if df is None:
                continue
            sig = check_signal(df, name)
            if sig:
                send_telegram(sig["msg"] + f" | Daily {daily_pnl}€")
                # Simu PnL - remplace par API Capital.com si tu veux auto-execution
                # capital_api.place_order(...)
            else:
                print(f"{name}: ATTENTE Close {df['Close'].iloc[-1]:.2f}")
        
        print(f"Sleep {CHECK_MINUTES} min - Daily PnL {daily_pnl}€")
        time.sleep(CHECK_MINUTES*60)

if __name__ == "__main__":
    main()
