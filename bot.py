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
MAX_SIGNALS_PER_RUN = 5          # 5 إشارات/دورة (تقليل ~50%)
TELEGRAM_COOLDOWN = 6            
MEXC_DELAY = 0.5                   

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

# ========== دوال مساعدة ==========
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
    """حساب قوة الإشارة (0-100) للفلترة"""
    score = 50
    
    # RSI
    rsi = ta.momentum.rsi(df['close'], window=14).iloc[-1]
    if direction == "LONG":
        if 50 < rsi < 65: score += 15
        elif rsi > 65: score += 5
    else:
        if 35 < rsi < 50: score += 15
        elif rsi < 35: score += 5
    
    # حجم التداول
    avg_vol = df['volume'].rolling(20).mean().iloc[-1]
    curr_vol = df['volume'].iloc[-1]
    if curr_vol > avg_vol * 1.5: score += 15
    elif curr_vol > avg_vol: score += 5
    
    # ADX
    try:
        adx = ta.trend.adx(df['high'], df['low'], df['close'], window=14).iloc[-1]
        if adx > 25: score += 10
    except:
        pass
    
    # مكافأة للاستراتيجيات
    if strategy == "MACD Cross": score += 5
    elif strategy == "BB Breakout": score += 10
    
    return min(score, 100)

def generate_summary(direction, strategy, df, tp1, tp4, sl):
    rsi_val = round(ta.momentum.rsi(df['close'], window=14).iloc[-1], 1)
    
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
    else:
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

    return f"📊 {structure_txt} {action_txt} {rsi_txt} {levels_txt}"

def send_safe(signal_data):
    """إرسال آمن مع التحقق من الرد"""
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

# ========== الدالة الرئيسية ==========
def analyze_and_trade():
    print(f"\n{'='*60}")
    print(f"🚀 15M Scalp Scan Started - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    exchange = ccxt.mexc()
    all_signals = []
    
    # ========== المرحلة 1: جمع الإشارات ==========
    for i, symbol in enumerate(SYMBOLS):
        time.sleep(MEXC_DELAY)
        
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=100)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            current_close = df['close'].iloc[-1]
            decimals = get_decimals(current_close)
            
            # --- Strategy 1: EMA Cross ---
            df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
            df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
            ema_buy = (df['ema_9'].iloc[-2] < df['ema_21'].iloc[-2]) and (df['ema_9'].iloc[-1] > df['ema_21'].iloc[-1])
            ema_sell = (df['ema_9'].iloc[-2] > df['ema_21'].iloc[-2]) and (df['ema_9'].iloc[-1] < df['ema_21'].iloc[-1])

            # --- Strategy 2: MACD ---
            macd_hist = ta.trend.macd_diff(df['close'])
            macd_buy = (macd_hist.iloc[-2] < 0) and (macd_hist.iloc[-1] > 0)
            macd_sell = (macd_hist.iloc[-2] > 0) and (macd_hist.iloc[-1] < 0)

            # --- Strategy 3: Bollinger Bands ---
            bb = ta.volatility.BollingerBands(close=df['close'], window=20, window_dev=2)
            curr_upper = bb.bollinger_hband().iloc[-1]
            curr_lower = bb.bollinger_lband().iloc[-1]
            prev_upper = bb.bollinger_hband().iloc[-2]
            prev_lower = bb.bollinger_lband().iloc[-2]
            
            bb_buy = (df['close'].iloc[-2] <= prev_upper) and (current_close > curr_upper)
            bb_sell = (df['close'].iloc[-2] >= prev_lower) and (current_close < curr_lower)

            # --- تسجيل الإشارات مع القوة ---
            if ema_buy or macd_buy or bb_buy:
                strategy_name = "EMA Cross" if ema_buy else ("MACD Cross" if macd_buy else "BB Breakout")
                lev = "15" if ema_buy else ("25" if macd_buy else "20")
                
                strength = calculate_signal_strength(df, "LONG", strategy_name)
                
                all_signals.append({
                    "symbol": symbol,
                    "direction": "LONG",
                    "strategy": strategy_name,
                    "leverage": lev,
                    "entry": round(current_close, decimals),
                    "strength": strength,
                    "df": df.copy(),
                    "decimals": decimals
                })
                print(f"  📈 {symbol} LONG via {strategy_name} (strength: {strength})")
                
            elif ema_sell or macd_sell or bb_sell:
                strategy_name = "EMA Cross" if ema_sell else ("MACD Cross" if macd_sell else "BB Breakdown")
                lev = "15" if ema_sell else ("25" if macd_sell else "20")
                
                strength = calculate_signal_strength(df, "SHORT", strategy_name)
                
                all_signals.append({
                    "symbol": symbol,
                    "direction": "SHORT",
                    "strategy": strategy_name,
                    "leverage": lev,
                    "entry": round(current_close, decimals),
                    "strength": strength,
                    "df": df.copy(),
                    "decimals": decimals
                })
                print(f"  📉 {symbol} SHORT via {strategy_name} (strength: {strength})")
                
        except Exception as e:
            print(f"  ⚠️ Error {symbol}: {e}")
            continue
    
    print(f"\n📊 Total signals found: {len(all_signals)}")
    
    # ========== المرحلة 2: فلترة ذكية ==========
    if not all_signals:
        print("❌ No signals found this cycle")
        return
    
    # 1. رتب حسب القوة
    all_signals.sort(key=lambda x: x["strength"], reverse=True)
    
    # 2. خذ Top 5
    top_signals = all_signals[:MAX_SIGNALS_PER_RUN]
    
    # 3. تأكد من تنوع الاستراتيجيات (3 أنواع كحد أقصى)
    strategies_used = set()
    final_signals = []
    
    for sig in top_signals:
        if len(final_signals) >= MAX_SIGNALS_PER_RUN:
            break
        # السماح بـ 3 استراتيجيات مختلفة
        if sig["strategy"] not in strategies_used or len(strategies_used) < 3:
            final_signals.append(sig)
            strategies_used.add(sig["strategy"])
    
    # ========== المرحلة 3: إرسال ==========
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
        
        summary = generate_summary(direction, sig["strategy"], sig["df"], tp1, tp4, sl)
        
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
    print("15M Scalp Bot started (v2.1 - Filtered Top 5)")
    analyze_and_trade()