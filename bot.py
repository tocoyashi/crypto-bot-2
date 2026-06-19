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

SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
    "ADA/USDT", "DOGE/USDT", "TRX/USDT", "AVAX/USDT", "LINK/USDT",
    "DOT/USDT", "POL/USDT", "SHIB/USDT", "LTC/USDT", "UNI/USDT",
    "ATOM/USDT", "XLM/USDT", "NEAR/USDT", "APT/USDT", "SUI/USDT",
    "ARB/USDT", "OP/USDT", "INJ/USDT", "TIA/USDT", "FIL/USDT",
    "AAVE/USDT", "GRT/USDT", "PEPE/USDT", "FET/USDT", "FLOKI/USDT",
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

def get_next_signal_id():
    filename = "signal_counter_15m.txt" # Changed filename so it doesn't conflict with the 4H bot
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

# Summary function customized for 15m Scalping Strategies
def generate_summary(direction, strategy, df, tp1, tp4, sl):
    rsi_val = round(ta.momentum.rsi(df['close'], window=14).iloc[-1], 1)
    
    # Structure
    if df['close'].iloc[-1] > df['close'].ewm(span=50, adjust=False).mean().iloc[-1]:
        structure_txt = random.choice([
            "15M chart indicates a short-term bullish bias with price trading above key moving averages.",
            "Intraday structure leans bullish as the 15M EMAs maintain an upward slope.",
            "The 15M timeframe shows bullish momentum holding above dynamic support levels."
        ])
    else:
        structure_txt = random.choice([
            "15M chart indicates a short-term bearish bias with price trading below key moving averages.",
            "Intraday structure leans bearish as the 15M EMAs maintain a downward slope.",
            "The 15M timeframe shows bearish momentum holding below dynamic resistance levels."
        ])

    # Action based on Strategy
    if "EMA" in strategy:
        if direction == "LONG":
            action_txt = random.choice([
                "A fast EMA 9/21 bullish crossover confirms immediate buying pressure.",
                "Short-term EMAs have aligned bullishly, triggering a scalping long setup.",
                "Price crossed above the fast EMA, indicating a sudden shift in intraday momentum."
            ])
        else:
            action_txt = random.choice([
                "A fast EMA 9/21 bearish crossover confirms immediate selling pressure.",
                "Short-term EMAs have aligned bearishly, triggering a scalping short setup.",
                "Price crossed below the fast EMA, indicating a sudden shift in intraday momentum."
            ])
    elif "MACD" in strategy:
        if direction == "LONG":
            action_txt = random.choice([
                "MACD histogram just flipped positive, signaling a strong intraday bullish divergence.",
                "A bullish MACD crossover on the 15M chart confirms the start of a short-term pump.",
                "Momentum is shifting upwards as the MACD line crosses above the signal line."
            ])
        else:
            action_txt = random.choice([
                "MACD histogram just flipped negative, signaling a strong intraday bearish divergence.",
                "A bearish MACD crossover on the 15M chart confirms the start of a short-term drop.",
                "Momentum is shifting downwards as the MACD line crosses below the signal line."
            ])
    else: # BB Breakout
        if direction == "LONG":
            action_txt = random.choice([
                "Price broke out aggressively above the upper Bollinger Band, showing extreme volatility.",
                "A 15M BB breakout to the upside indicates a sudden surge in buying power.",
                "Breaking the upper band suggests an explosive short-term move is underway."
            ])
        else:
            action_txt = random.choice([
                "Price broke down aggressively below the lower Bollinger Band, showing extreme volatility.",
                "A 15M BB breakdown to the downside indicates a sudden surge in selling power.",
                "Breaking the lower band suggests an explosive short-term drop is underway."
            ])

    # RSI
    if direction == "LONG":
        if rsi_val < 70:
            rsi_txt = random.choice([
                f"RSI at {rsi_val} shows healthy momentum with room before overbought levels.",
                f"Intraday RSI reads {rsi_val}, confirming buyers are in control."
            ])
        else:
            rsi_txt = random.choice([
                f"RSI is extremely strong at {rsi_val}, riding the overbought momentum.",
                f"RSI reads {rsi_val}, showing massive buying intensity on the 15M frame."
            ])
    else:
        if rsi_val > 30:
            rsi_txt = random.choice([
                f"RSI at {rsi_val} shows healthy downside momentum with room before oversold levels.",
                f"Intraday RSI reads {rsi_val}, confirming sellers are in control."
            ])
        else:
            rsi_txt = random.choice([
                f"RSI is extremely weak at {rsi_val}, riding the oversold momentum.",
                f"RSI reads {rsi_val}, showing massive selling intensity on the 15M frame."
            ])

    # Levels
    if direction == "LONG":
        levels_txt = random.choice([
            f"Invalidation of this scalping setup is below {sl}; aiming for a quick sweep to {tp1} and extension to {tp4}.",
            f"Risk is strictly managed under {sl}; expecting a fast move to secure {tp1} initially.",
            f"Stop loss is placed at {sl}; looking for a rapid execution towards {tp1}."
        ])
    else:
        levels_txt = random.choice([
            f"Invalidation of this scalping setup is above {sl}; aiming for a quick drop to {tp1} and extension to {tp4}.",
            f"Risk is strictly managed above {sl}; expecting a fast move to secure {tp1} initially.",
            f"Stop loss is placed at {sl}; looking for a rapid execution towards {tp1}."
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

    # Updated text with Bold HTML tags
    text = f"🔖 <b>Signal ID: {signal_id}</b>\n📩 #{clean_name} {TIMEFRAME.upper()} | {strategy}\n{trend_emoji} {direction_text} Entry Zone: {zone_low}-{zone_high}\n⚡ Leverage: {leverage}x\n\n🎯 Strategy Details:\nTarget 1: {tp1}\nTarget 2: {tp2}\nTarget 3: {tp3}\nTarget 4: {tp4}\n\n🔺 Stop-Loss: {sl}\n💡 After reaching the first target you can put the rest of the position to breakeven.\n\n<b>{summary_text}</b>"

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHANNEL_ID, "text": text, "disable_web_page_preview": True, "parse_mode": "HTML"}
    try:
        response = requests.post(url, json=payload)
        if response.json().get('ok'): print(f"Signal {signal_id} sent for {coin_name} via {strategy}")
        else: print(f"ERROR for {coin_name}: {response.json().get('description')}")
    except Exception as e: print(f"Network error: {e}")

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
                
                # Generate summary for Long
                summary = generate_summary("LONG", strategy_name, df, round(entry * 1.0075, decimals), round(entry * 1.058, decimals), round(entry * 0.95, decimals))
                
                send_crypto_signal(symbol, "LONG", strategy_name, entry, lev, round(entry * 1.0075, decimals), round(entry * 1.017, decimals), round(entry * 1.032, decimals), round(entry * 1.058, decimals), round(entry * 0.95, decimals), summary)
                time.sleep(6) # Increased to 6s for Cornix compatibility
                
            # ✨ SHORT Signals
            elif ema_sell or macd_sell or bb_sell:
                strategy_name = "EMA Cross" if ema_sell else ("MACD Cross" if macd_sell else "BB Breakdown")
                lev = "15" if ema_sell else ("25" if macd_sell else "20")
                
                print(f"SELL on {symbol} via {strategy_name} ({lev}x)!")
                entry = round(current_close, decimals)
                
                # Generate summary for Short
                summary = generate_summary("SHORT", strategy_name, df, round(entry * 0.9925, decimals), round(entry * 0.942, decimals), round(entry * 1.05, decimals))
                
                send_crypto_signal(symbol, "SHORT", strategy_name, entry, lev, round(entry * 0.9925, decimals), round(entry * 0.983, decimals), round(entry * 0.968, decimals), round(entry * 0.942, decimals), round(entry * 1.05, decimals), summary)
                time.sleep(6) # Increased to 6s for Cornix compatibility
            else:
                pass # No signal
                
        except Exception as e:
            print(f"Error {symbol}: {e}")

if __name__ == "__main__":
    print("15M Scalp Bot started...")
    analyze_and_trade()