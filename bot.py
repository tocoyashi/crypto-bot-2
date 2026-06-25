import os
import ssl
import json
import time
import random
from datetime import datetime, timedelta

ssl._create_default_https_context = ssl._create_unverified_context

import ccxt
import pandas as pd
import ta
import requests

# ========== إعدادات البوت ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
TIMEFRAME = "15m"

# ========== حدود Rate Limiting ==========
MAX_SIGNALS_PER_RUN = 5
TELEGRAM_COOLDOWN = 6
MEXC_DELAY = 0.5

# ========== وضع التسامح ==========
RELAXED_MODE = False  # True = أقل فلترة

# ========== قائمة العملات (50 عملة) ==========
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

def calculate_signal_strength(df, direction, strategy):
    """فلترة أخف - تسمح بمزيد من الإشارات"""
    if RELAXED_MODE:
        return 70  # لا فلترة
    
    score = 50
    
    # RSI - أخفف
    rsi = ta.momentum.rsi(df['close'], window=14).iloc[-1]
    if direction == "LONG":
        if rsi > 50: score += 10
        if rsi > 60: score += 5
    else:
        if rsi < 50: score += 10
        if rsi < 40: score += 5
    
    # الحجم - أخفف
    avg_vol = df['volume'].rolling(20).mean().iloc[-1]
    curr_vol = df['volume'].iloc[-1]
    if curr_vol > avg_vol * 0.8: score += 10
    if curr_vol > avg_vol * 1.5: score += 5
    
    # ADX - أخفف
    try:
        adx = ta.trend.adx(df['high'], df['low'], df['close'], window=14).iloc[-1]
        if adx > 15: score += 10
    except:
        pass
    
    # استراتيجية
    if strategy == "MACD Cross": score += 5
    elif strategy == "BB Breakout": score += 10
    
    return min(score, 100)

# ========== تحليل ذكي بدون أرقام ==========
def analyze_market_structure(df):
    price = df['close'].iloc[-1]
    ema_50 = df['close'].ewm(span=50, adjust=False).mean().iloc[-1]
    ema_200 = df['close'].ewm(span=200, adjust=False).mean().iloc[-1] if len(df) > 200 else ema_50
    
    if price > ema_50 > ema_200:
        return "bullish_trend"
    elif price < ema_50 < ema_200:
        return "bearish_trend"
    elif price > ema_50:
        return "bullish_correction"
    else:
        return "bearish_correction"

def analyze_volume_profile(df):
    curr_vol = df['volume'].iloc[-1]
    avg_vol = df['volume'].rolling(20).mean().iloc[-1]
    prev_vol = df['volume'].iloc[-2]
    
    if curr_vol > avg_vol * 1.5 and curr_vol > prev_vol:
        return "surge"
    elif curr_vol > avg_vol:
        return "above_average"
    elif curr_vol < avg_vol * 0.5:
        return "thin"
    else:
        return "normal"

def analyze_momentum(df, direction):
    rsi = ta.momentum.rsi(df['close'], window=14).iloc[-1]
    
    if direction == "LONG":
        if rsi > 70: return "overbought"
        elif rsi > 55: return "strong"
        elif rsi > 45: return "neutral"
        else: return "weak"
    else:
        if rsi < 30: return "oversold"
        elif rsi < 45: return "strong"
        elif rsi < 55: return "neutral"
        else: return "weak"

def analyze_candle_pressure(df, direction):
    last = df.iloc[-1]
    body = abs(last['close'] - last['open'])
    upper_wick = last['high'] - max(last['close'], last['open'])
    lower_wick = min(last['close'], last['open']) - last['low']
    
    if direction == "LONG":
        if lower_wick > body * 1.5: return "strong_rejection"
        elif body > df['close'].rolling(20).std().iloc[-1] * 2: return "momentum_candle"
        else: return "normal"
    else:
        if upper_wick > body * 1.5: return "strong_rejection"
        elif body > df['close'].rolling(20).std().iloc[-1] * 2: return "momentum_candle"
        else: return "normal"

def generate_smart_summary(direction, strategy, df):
    structure = analyze_market_structure(df)
    volume = analyze_volume_profile(df)
    momentum = analyze_momentum(df, direction)
    candle = analyze_candle_pressure(df, direction)
    
    structure_map = {
        "bullish_trend": {
            "LONG": "Price is trading within a well-established uptrend, holding above key dynamic supports.",
            "SHORT": "Price is pulling back within a broader uptrend, approaching a potential reversal zone."
        },
        "bearish_trend": {
            "LONG": "Price is attempting a counter-trend bounce from oversold conditions.",
            "SHORT": "Price is trading within a confirmed downtrend, respecting dynamic resistance levels."
        },
        "bullish_correction": {
            "LONG": "Price is recovering from a minor pullback, showing early signs of trend resumption.",
            "SHORT": "Price is struggling at resistance after a weak bounce, suggesting further downside."
        },
        "bearish_correction": {
            "LONG": "Price is finding support after a brief decline, with buyers stepping in.",
            "SHORT": "Price is rolling over after a corrective bounce, resuming the downward path."
        }
    }
    
    volume_map = {
        "surge": "Trading volume is surging significantly, confirming strong participation behind this move.",
        "above_average": "Volume is picking up above average levels, adding conviction to the setup.",
        "normal": "Volume is steady and in line with recent sessions.",
        "thin": "Volume is relatively thin, suggesting caution and lower conviction."
    }
    
    momentum_map_long = {
        "overbought": "Momentum is running hot into overbought territory, suggesting a powerful but risky push.",
        "strong": "Momentum is building healthily with room to extend before reaching extreme levels.",
        "neutral": "Momentum is balanced, neither overextended nor exhausted.",
        "weak": "Momentum is subdued, requiring confirmation before full commitment."
    }
    momentum_map_short = {
        "oversold": "Momentum is diving deep into oversold territory, indicating a powerful but risky selloff.",
        "strong": "Bearish momentum is accelerating with room to extend before reaching extreme levels.",
        "neutral": "Momentum is balanced, neither overextended nor exhausted.",
        "weak": "Momentum is subdued, requiring confirmation before full commitment."
    }
    
    candle_map = {
        "strong_rejection": {
            "LONG": "The latest candle shows a strong rejection from lower levels, signaling aggressive buying.",
            "SHORT": "The latest candle shows a strong rejection from higher levels, signaling aggressive selling."
        },
        "momentum_candle": {
            "LONG": "A large bullish momentum candle confirms buyers are in full control.",
            "SHORT": "A large bearish momentum candle confirms sellers are in full control."
        },
        "normal": {
            "LONG": "Price action is constructive with steady buying pressure.",
            "SHORT": "Price action is constructive with steady selling pressure."
        }
    }
    
    strategy_context = {
        "EMA Cross": {
            "LONG": "The fast moving average has crossed above the slower one, triggering a fresh bullish alignment.",
            "SHORT": "The fast moving average has crossed below the slower one, triggering a fresh bearish alignment."
        },
        "MACD Cross": {
            "LONG": "The momentum oscillator has flipped positive, confirming a shift in underlying pressure.",
            "SHORT": "The momentum oscillator has flipped negative, confirming a shift in underlying pressure."
        },
        "BB Breakout": {
            "LONG": "Price has expanded beyond the upper volatility band, signaling a volatility expansion to the upside.",
            "SHORT": "Price has collapsed below the lower volatility band, signaling a volatility expansion to the downside."
        },
        "BB Breakdown": {
            "LONG": "Price has expanded beyond the upper volatility band, signaling a volatility expansion to the upside.",
            "SHORT": "Price has collapsed below the lower volatility band, signaling a volatility expansion to the downside."
        }
    }
    
    risk_map = {
        "LONG": {
            "EMA Cross": "Consider scaling in gradually as the moving average alignment confirms.",
            "MACD Cross": "Wait for a minor pullback to the breakout zone for better risk-reward.",
            "BB Breakout": "This is a momentum play; keep position size conservative due to volatility expansion."
        },
        "SHORT": {
            "EMA Cross": "Consider scaling in gradually as the moving average alignment confirms.",
            "MACD Cross": "Wait for a minor bounce to the breakdown zone for better risk-reward.",
            "BB Breakdown": "This is a momentum play; keep position size conservative due to volatility expansion."
        }
    }
    
    parts = [
        structure_map[structure][direction],
        strategy_context[strategy][direction],
        candle_map[candle][direction],
        volume_map[volume],
        momentum_map_long[momentum] if direction == "LONG" else momentum_map_short[momentum],
        risk_map[direction][strategy]
    ]
    
    return " ".join(parts)

def send_safe(signal_data):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": signal_data["text"],
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()
        if data.get("ok"):
            print(f"✅ Signal {signal_data['id']} sent for {signal_data['symbol']}")
            return True
        if data.get("error_code") == 429:
            retry_after = data.get("parameters", {}).get("retry_after", 60)
            print(f"🚫 Flood! Wait {retry_after}s")
            time.sleep(retry_after)
            return False
        print(f"❌ Telegram error: {data.get('description')}")
        return False
    except Exception as e:
        print(f"❌ Network error: {e}")
        return False

def send_crypto_signal(coin_name, direction, strategy, entry, leverage, tp1, tp2, tp3, tp4, sl, summary_text):
    signal_id = get_next_signal_id()
    trend_emoji = "📈" if direction.lower() == "long" else "📉"
    direction_text = "Long" if direction.lower() == "long" else "Short"
    clean_name = coin_name.replace("/", "")
    
    zone_low = round(entry * 0.9985, get_decimals(entry))
    zone_high = round(entry * 1.0015, get_decimals(entry))

    text = f"""🔖 <b>Signal ID: {signal_id}</b>
📩 #{clean_name} {TIMEFRAME.upper()} | {strategy}
{trend_emoji} {direction_text} Entry Zone: {zone_low}-{zone_high}
⚡ Leverage: {leverage}x

🎯 Strategy Details:
Target 1: {tp1}
Target 2: {tp2}
Target 3: {tp3}
Target 4: {tp4}

🔺 Stop-Loss: {sl}
💡 After reaching the first target you can put the rest of the position to breakeven.

<b>{summary_text}</b>"""

    return send_safe({
        "id": signal_id,
        "symbol": coin_name,
        "text": text
    })

def analyze_and_trade():
    print(f"\n{'='*60}")
    print(f"🚀 15M Scalp Scan Started - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    exchange = ccxt.mexc()
    all_signals = []
    
    for i, symbol in enumerate(SYMBOLS):
        time.sleep(MEXC_DELAY)
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=100)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            current_close = df['close'].iloc[-1]
            decimals = get_decimals(current_close)
            
            df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
            df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
            ema_buy = (df['ema_9'].iloc[-2] < df['ema_21'].iloc[-2]) and (df['ema_9'].iloc[-1] > df['ema_21'].iloc[-1])
            ema_sell = (df['ema_9'].iloc[-2] > df['ema_21'].iloc[-2]) and (df['ema_9'].iloc[-1] < df['ema_21'].iloc[-1])

            macd_hist = ta.trend.macd_diff(df['close'])
            macd_buy = (macd_hist.iloc[-2] < 0) and (macd_hist.iloc[-1] > 0)
            macd_sell = (macd_hist.iloc[-2] > 0) and (macd_hist.iloc[-1] < 0)

            bb = ta.volatility.BollingerBands(close=df['close'], window=20, window_dev=2)
            curr_upper = bb.bollinger_hband().iloc[-1]
            curr_lower = bb.bollinger_lband().iloc[-1]
            prev_upper = bb.bollinger_hband().iloc[-2]
            prev_lower = bb.bollinger_lband().iloc[-2]
            
            bb_buy = (df['close'].iloc[-2] <= prev_upper) and (current_close > curr_upper)
            bb_sell = (df['close'].iloc[-2] >= prev_lower) and (current_close < curr_lower)

            if ema_buy or macd_buy or bb_buy:
                strategy_name = "EMA Cross" if ema_buy else ("MACD Cross" if macd_buy else "BB Breakout")
                lev = "15" if ema_buy else ("25" if macd_buy else "20")
                strength = calculate_signal_strength(df, "LONG", strategy_name)
                all_signals.append({
                    "symbol": symbol, "direction": "LONG", "strategy": strategy_name,
                    "leverage": lev, "entry": round(current_close, decimals),
                    "strength": strength, "df": df.copy(), "decimals": decimals
                })
                print(f"  📈 {symbol} LONG via {strategy_name} (strength: {strength})")
                
            elif ema_sell or macd_sell or bb_sell:
                strategy_name = "EMA Cross" if ema_sell else ("MACD Cross" if macd_sell else "BB Breakdown")
                lev = "15" if ema_sell else ("25" if macd_sell else "20")
                strength = calculate_signal_strength(df, "SHORT", strategy_name)
                all_signals.append({
                    "symbol": symbol, "direction": "SHORT", "strategy": strategy_name,
                    "leverage": lev, "entry": round(current_close, decimals),
                    "strength": strength, "df": df.copy(), "decimals": decimals
                })
                print(f"  📉 {symbol} SHORT via {strategy_name} (strength: {strength})")
                
        except Exception as e:
            print(f"  ⚠️ Error {symbol}: {e}")
            continue
    
    print(f"\n📊 Total signals found: {len(all_signals)}")
    
    if not all_signals:
        print("❌ No signals found this cycle")
        return
    
    all_signals.sort(key=lambda x: x["strength"], reverse=True)
    top_signals = all_signals[:MAX_SIGNALS_PER_RUN]
    
    strategies_used = set()
    final_signals = []
    for sig in top_signals:
        if len(final_signals) >= MAX_SIGNALS_PER_RUN:
            break
        if sig["strategy"] not in strategies_used or len(strategies_used) < 3:
            final_signals.append(sig)
            strategies_used.add(sig["strategy"])
    
    print(f"\n{'='*60}")
    print(f"🎯 Sending TOP {len(final_signals)} signals (rejected {len(all_signals) - len(final_signals)})")
    print(f"{'='*60}")
    
    sent_count = 0
    for sig in final_signals:
        entry = sig["entry"]
        decimals = sig["decimals"]
        direction = sig["direction"]
        
        if direction == "LONG":
            tp1 = round(entry * 1.0075, decimals)
            tp2 = round(entry * 1.017, decimals)
            tp3 = round(entry * 1.032, decimals)
            tp4 = round(entry * 1.058, decimals)
            sl = round(entry * 0.95, decimals)
        else:
            tp1 = round(entry * 0.9925, decimals)
            tp2 = round(entry * 0.983, decimals)
            tp3 = round(entry * 0.968, decimals)
            tp4 = round(entry * 0.942, decimals)
            sl = round(entry * 1.05, decimals)
        
        summary = generate_smart_summary(direction, sig["strategy"], sig["df"])
        
        success = send_crypto_signal(
            sig["symbol"], direction, sig["strategy"], entry,
            sig["leverage"], tp1, tp2, tp3, tp4, sl, summary
        )
        
        if success:
            sent_count += 1
            time.sleep(TELEGRAM_COOLDOWN)
        else:
            print(f"⚠️ Failed to send {sig['symbol']}, skipping...")
    
    print(f"\n{'='*60}")
    print(f"✅ Cycle complete: {sent_count}/{len(final_signals)} sent")
    print(f"🗑️ Rejected: {len(all_signals) - len(final_signals)} signals")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    print("15M Scalp Bot started (v3.1 - Relaxed Filter)")
    analyze_and_trade()
