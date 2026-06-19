import os
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import ccxt
import pandas as pd
import ta
import requests
import time
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

TIMEFRAME = "15m"

SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
    "ADA/USDT", "DOGE/USDT", "TRX/USDT", "AVAX/USDT", "LINK/USDT",
    "DOT/USDT", "POL/USDT", "SHIB/USDT", "LTC/USDT", "UNI/USDT",
    "ATOM/USDT", "XLM/USDT", "NEAR/USDT", "APT/USDT", "SUI/USDT",
    "ARB/USDT", "OP/USDT", "INJ/USDT", "TIA/USDT", "FIL/USDT",
    "AAVE/USDT", "GRT/USDT", "PEPE/USDT", "FET/USDT", "TON/USDT",
    "WIF/USDT", "SEI/USDT", "ETC/USDT", "ICP/USDT", "WLD/USDT",
    "IMX/USDT", "RENDER/USDT", "JUP/USDT", "STRK/USDT", "BONK/USDT",
    "ONDO/USDT", "PYTH/USDT", "ENA/USDT", "ORDI/USDT", "KAS/USDT",
    "MINA/USDT", "JTO/USDT", "BLUR/USDT", "API3/USDT", "W/USDT"
]

def get_decimals(price):
    if price > 100: return 2
    elif price > 1: return 3
    elif price > 0.01: return 5
    else: return 8

def send_crypto_signal(coin_name, direction, strategy, entry, tp1, tp2, tp3, tp4, sl):
    trend_emoji = "📈" if direction.lower() == "long" else "📉"
    direction_text = "Long" if direction.lower() == "long" else "Short"
    clean_name = coin_name.replace("/", "")
    
    zone_low = round(entry * 0.9985, get_decimals(entry))
    zone_high = round(entry * 1.0015, get_decimals(entry))

    text = f"📩 #{clean_name} {TIMEFRAME.upper()} | {strategy}\n{trend_emoji} {direction_text} Entry Zone: {zone_low}-{zone_high}\n\n🎯 Strategy: EMA / MACD / BB Breakout\n\n⏳ Signal Details:\nTarget 1: {tp1}\nTarget 2: {tp2}\nTarget 3: {tp3}\nTarget 4: {tp4}\n\n🔺 Stop-Loss: {sl}\n💡 After reaching the first target you can put the rest of the position to breakeven."

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHANNEL_ID, "text": text, "disable_web_page_preview": True}
    try:
        response = requests.post(url, json=payload)
        if response.json().get('ok'): print(f"Signal sent for {coin_name} via {strategy}")
        else: print(f"ERROR for {coin_name}: {response.json().get('description')}")
    except Exception as e: print(f"Network error: {e}")

def analyze_and_trade():
    print("Starting scan with 3 Strategies (EMA + MACD + BB)...")
    exchange = ccxt.mexc()
    
    for symbol in SYMBOLS:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=100)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Strategy 1: EMA
            df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
            df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
            ema_buy = (df['ema_9'].iloc[-2] < df['ema_21'].iloc[-2]) and (df['ema_9'].iloc[-1] > df['ema_21'].iloc[-1])
            ema_sell = (df['ema_9'].iloc[-2] > df['ema_21'].iloc[-2]) and (df['ema_9'].iloc[-1] < df['ema_21'].iloc[-1])

            # Strategy 2: MACD
            macd_hist = ta.trend.macd_diff(df['close'])
            macd_buy = (macd_hist.iloc[-2] < 0) and (macd_hist.iloc[-1] > 0)
            macd_sell = (macd_hist.iloc[-2] > 0) and (macd_hist.iloc[-1] < 0)

            # Strategy 3: Bollinger Bands Breakout
            bb = ta.volatility.BollingerBands(close=df['close'], window=20, window_dev=2)
            curr_upper = bb.bollinger_hband().iloc[-1]
            curr_lower = bb.bollinger_lband().iloc[-1]
            prev_upper = bb.bollinger_hband().iloc[-2]
            prev_lower = bb.bollinger_lband().iloc[-2]
            current_close = df['close'].iloc[-1]
            
            bb_buy = (df['close'].iloc[-2] <= prev_upper) and (current_close > curr_upper)
            bb_sell = (df['close'].iloc[-2] >= prev_lower) and (current_close < curr_lower)

            decimals = get_decimals(current_close)
            
            if ema_buy or macd_buy or bb_buy:
                strategy_name = "EMA Cross" if ema_buy else ("MACD Cross" if macd_buy else "BB Breakout")
                print(f"BUY on {symbol} via {strategy_name}!")
                entry = round(current_close, decimals)
                send_crypto_signal(symbol, "LONG", strategy_name, entry, round(entry * 1.0075, decimals), round(entry * 1.017, decimals), round(entry * 1.032, decimals), round(entry * 1.058, decimals), round(entry * 0.95, decimals))
                time.sleep(2)
                
            elif ema_sell or macd_sell or bb_sell:
                strategy_name = "EMA Cross" if ema_sell else ("MACD Cross" if macd_sell else "BB Breakdown")
                print(f"SELL on {symbol} via {strategy_name}!")
                entry = round(current_close, decimals)
                send_crypto_signal(symbol, "SHORT", strategy_name, entry, round(entry * 0.9925, decimals), round(entry * 0.983, decimals), round(entry * 0.968, decimals), round(entry * 0.942, decimals), round(entry * 1.05, decimals))
                time.sleep(2)
            else:
                print(f"No signal for {symbol}.")
                
        except Exception as e:
            print(f"Error {symbol}: {e}")

if __name__ == "__main__":
    print("Bot started...")
    analyze_and_trade()