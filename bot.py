import os
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import ccxt
import pandas as pd
import ta
import requests
import time
import random

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

TIMEFRAME = "15m"

# ========== 38 عملة (حذفنا 12) ==========
SYMBOLS = [
    "BTC/USDT", "ADA/USDT", "DOGE/USDT", "TRX/USDT", "AVAX/USDT",
    "LINK/USDT", "DOT/USDT", "POL/USDT", "SHIB/USDT", "LTC/USDT",
    "UNI/USDT", "ATOM/USDT", "XLM/USDT", "NEAR/USDT", "APT/USDT",
    "SUI/USDT", "ARB/USDT", "OP/USDT", "INJ/USDT", "AAVE/USDT",
    "GRT/USDT", "PEPE/USDT", "FET/USDT", "FLOKI/USDT", "WIF/USDT",
    "SEI/USDT", "ICP/USDT", "WLD/USDT", "IMX/USDT", "RENDER/USDT",
    "JUP/USDT", "STRK/USDT", "BONK/USDT", "ONDO/USDT", "PYTH/USDT",
    "ENA/USDT", "ORDI/USDT", "KAS/USDT"
]

def get_decimals(price):
    if price > 100: return 2
    elif price > 1: return 3
    elif price > 0.01: return 5
    else: return 8

def get_next_signal_id():
    filename = "signal_counter_15m.txt"
    try:
        with open(filename, "r") as file:
            current_id = int(file.read().strip())
    except (FileNotFoundError, ValueError):
        current_id = 0
    
    next_id = current_id + 1
    
    try:
        with open(filename, "w") as file:
            file.write(str(next_id))
    except Exception as e:
        print(f"Error saving signal ID: {e}")
        
    return f"{next_id:03d}"

# ========== تحليل بدون أرقام ==========
def generate_summary(direction, strategy, df):
    rsi_val = round(ta.momentum.rsi(df['close'], window=14).iloc[-1], 1)
    
    # الهيكل السعري (بدون أرقام)
    if df['close'].iloc[-1] > df['close'].ewm(span=50, adjust=False).mean().iloc[-1]:
        structure_txt = random.choice([
            "The intraday chart maintains a bullish posture with price holding above dynamic support.",
            "Short-term structure favors buyers as momentum sustains above key averages.",
            "Price action on the fifteen-minute frame reflects steady bullish commitment."
        ])
    else:
        structure_txt = random.choice([
            "The intraday chart maintains a bearish posture with price holding below dynamic resistance.",
            "Short-term structure favors sellers as momentum sustains below key averages.",
            "Price action on the fifteen-minute frame reflects steady bearish commitment."
        ])

    # الحدث المُفَعِّل (بدون أرقام)
    if "EMA" in strategy:
        if direction == "LONG":
            action_txt = random.choice([
                "A fast exponential crossover has triggered fresh buying interest.",
                "Short-term averages aligned bullishly, opening a momentum scalp window.",
                "Price reclaimed the fast average, signaling a shift in micro-structure."
            ])
        else:
            action_txt = random.choice([
                "A fast exponential crossover has triggered fresh selling interest.",
                "Short-term averages aligned bearishly, opening a momentum scalp window.",
                "Price lost the fast average, signaling a shift in micro-structure."
            ])
    elif "MACD" in strategy:
        if direction == "LONG":
            action_txt = random.choice([
                "The momentum oscillator turned positive, confirming a bullish divergence.",
                "A fresh bullish cross on the momentum gauge suggests accelerating upside.",
                "Buying pressure intensified as the histogram flipped into positive territory."
            ])
        else:
            action_txt = random.choice([
                "The momentum oscillator turned negative, confirming a bearish divergence.",
                "A fresh bearish cross on the momentum gauge suggests accelerating downside.",
                "Selling pressure intensified as the histogram flipped into negative territory."
            ])
    else:  # BB
        if direction == "LONG":
            action_txt = random.choice([
                "An expansion beyond the upper volatility band signals a breakout impulse.",
                "Price stretched above the compression zone, indicating a volatility surge.",
                "The squeeze resolved to the upside with aggressive momentum."
            ])
        else:
            action_txt = random.choice([
                "An expansion beyond the lower volatility band signals a breakdown impulse.",
                "Price stretched below the compression zone, indicating a volatility surge.",
                "The squeeze resolved to the downside with aggressive momentum."
            ])

    # الزخم (وصف فقط، بدون ذكر الرقم)
    if direction == "LONG":
        if rsi_val < 70:
            rsi_txt = random.choice([
                "Momentum remains healthy with room before reaching extreme overbought conditions.",
                "The oscillator shows constructive buying pressure without overheating.",
                "Buyers maintain control as the momentum gauge sits in a sustainable zone."
            ])
        else:
            rsi_txt = random.choice([
                "Momentum is running hot, riding strong overbought conditions.",
                "The oscillator shows intense buying pressure at elevated levels.",
                "Buyers dominate with the momentum gauge deep in the upper extreme."
            ])
    else:
        if rsi_val > 30:
            rsi_txt = random.choice([
                "Momentum remains healthy with room before reaching extreme oversold conditions.",
                "The oscillator shows constructive selling pressure without capitulation.",
                "Sellers maintain control as the momentum gauge sits in a sustainable zone."
            ])
        else:
            rsi_txt = random.choice([
                "Momentum is running cold, riding strong oversold conditions.",
                "The oscillator shows intense selling pressure at depressed levels.",
                "Sellers dominate with the momentum gauge deep in the lower extreme."
            ])

    # مستويات المخاطر (بدون أرقام!)
    if direction == "LONG":
        levels_txt = random.choice([
            "Invalidation lies below the entry zone; target a quick sweep to the first objective and extension toward the final target.",
            "Risk is strictly managed beneath the entry area; expect a rapid move to secure initial profits.",
            "Place defensive stops below the setup zone; anticipate swift execution toward the nearest target."
        ])
    else:
        levels_txt = random.choice([
            "Invalidation lies above the entry zone; target a quick drop to the first objective and extension toward the final target.",
            "Risk is strictly managed above the entry area; expect a rapid move to secure initial profits.",
            "Place defensive stops above the setup zone; anticipate swift execution toward the nearest target."
        ])

    summary = f"📊 {structure_txt} {action_txt} {rsi_txt} {levels_txt}"
    return summary

def send_crypto_signal(coin_name, direction, strategy, entry, leverage, tp1, tp2, tp3, tp4, sl, summary_text):
    signal_id = get_next_signal_id()
    trend_emoji = "📈" if direction.lower() == "long" else "📉"
    direction_text = "Long" if direction.lower() == "long" else "Short"
    clean_name = coin_name.replace("/", "")
    
    zone_low = round(entry * 0.9985, get_decimals(entry))
    zone_high = round(entry * 1.0015, get_decimals(entry))

    text = f"🔖 <b>Signal ID: {signal_id}</b>\n📩 #{clean_name} {TIMEFRAME.upper()} | {strategy}\n{trend_emoji} {direction_text} Entry Zone: {zone_low}-{zone_high}\n⚡ Leverage: {leverage}x\n\n🎯 Strategy Details:\nTarget 1: {tp1}\nTarget 2: {tp2}\nTarget 3: {tp3}\nTarget 4: {tp4}\n\n🔺 Stop-Loss: {sl}\n💡 After reaching the first target you can put the rest of the position to breakeven.\n\n<b>{summary_text}</b>"

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHANNEL_ID, "text": text, "disable_web_page_preview": True, "parse_mode": "HTML"}
    try:
        response = requests.post(url, json=payload)
        if response.json().get('ok'): 
            print(f"Signal {signal_id} sent for {coin_name} via {strategy}")
        else: 
            print(f"ERROR for {coin_name}: {response.json().get('description')}")
    except Exception as e: 
        print(f"Network error: {e}")

def analyze_and_trade():
    print("Starting 15M Scalp Scan with Dynamic Leverage & 3 Strategies...")
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
            
            # ✨ LONG Signals
            if ema_buy or macd_buy or bb_buy:
                strategy_name = "EMA Cross" if ema_buy else ("MACD Cross" if macd_buy else "BB Breakout")
                lev = "15" if ema_buy else ("25" if macd_buy else "20")
                
                print(f"BUY on {symbol} via {strategy_name} ({lev}x)!")
                entry = round(current_close, decimals)
                
                # Generate summary for Long (بدون أرقام!)
                summary = generate_summary("LONG", strategy_name, df)
                
                send_crypto_signal(symbol, "LONG", strategy_name, entry, lev, round(entry * 1.0075, decimals), round(entry * 1.017, decimals), round(entry * 1.032, decimals), round(entry * 1.058, decimals), round(entry * 0.95, decimals), summary)
                time.sleep(6)
                
            # ✨ SHORT Signals
            elif ema_sell or macd_sell or bb_sell:
                strategy_name = "EMA Cross" if ema_sell else ("MACD Cross" if macd_sell else "BB Breakdown")
                lev = "15" if ema_sell else ("25" if macd_sell else "20")
                
                print(f"SELL on {symbol} via {strategy_name} ({lev}x)!")
                entry = round(current_close, decimals)
                
                # Generate summary for Short (بدون أرقام!)
                summary = generate_summary("SHORT", strategy_name, df)
                
                send_crypto_signal(symbol, "SHORT", strategy_name, entry, lev, round(entry * 0.9925, decimals), round(entry * 0.983, decimals), round(entry * 0.968, decimals), round(entry * 0.942, decimals), round(entry * 1.05, decimals), summary)
                time.sleep(6)
            else:
                pass
                
        except Exception as e:
            print(f"Error {symbol}: {e}")

if __name__ == "__main__":
    print("15M Scalp Bot started...")
    analyze_and_trade()
