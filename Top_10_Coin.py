import requests
from datetime import datetime
from zoneinfo import ZoneInfo
import time
import traceback

# ========== CẤU HÌNH ==========
VIETNAM_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")
TELEGRAM_BOT_TOKEN = "8226246719:AAHXDggFiFYpsgcq1vwTAWv7Gsz1URP4KEU"
TELEGRAM_CHAT_ID = "-4706073326"
RATE_PERCENT = 0.3
RATE_BODY = 0.66
RATE_NEN_01_02 = 0.2

# Danh sách coin cố định
SYMBOLS = [
    {"symbol": s, "candle_interval": "5m", "limit": 2}
    for s in [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "PUMPUSDT",
        "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "TRXUSDT", "TONUSDT",
        "LINKUSDT", "MATICUSDT", "DOTUSDT", "LTCUSDT", "SHIBUSDT",
        "AVAXUSDT", "UNIUSDT", "BCHUSDT", "ETCUSDT", "XLMUSDT",
        "ATOMUSDT", "XMRUSDT", "APTUSDT", "FILUSDT", "HBARUSDT",
        "VETUSDT", "NEARUSDT", "INJUSDT", "OPUSDT", "RNDRUSDT"
    ]
]

def send_telegram_alert(message, is_critical=False):
    try:
        prefix = "🚨 *CẢNH BÁO NGHIÊM TRỌNG* 🚨\n" if is_critical else "⚠️ *CẢNH BÁO* ⚠️\n"
        formatted_message = prefix + message
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": formatted_message,
                "parse_mode": "Markdown"
            },
            timeout=10
        )
    except Exception as e:
        print(f"⚠️ Telegram alert error: {e}")

def fetch_latest_candle(symbol_config):
    try:
        url = "https://fapi.binance.com/fapi/v1/klines"
        params = {
            "symbol": symbol_config["symbol"],
            "interval": symbol_config["candle_interval"],
            "limit": symbol_config["limit"]
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        # Lấy cây nến đóng cửa gần nhất
        candle_01 = data[-1]
        high_01 = float(candle_01[1])
        low_01 = float(candle_01[3])
        body_size_01 = abs(high_01 - low_01)
        # Lấy cây nến đóng cửa gần thứ 2
        candle_02 = data[-2]
        high_02 = float(candle_02[1])
        low_02 = float(candle_02[3])
        body_size_02 = abs(high_02 - low_02)
         # So sánh tỉ lệ cây nến đóng gần nhất với case nến trước đó
        if ((body_size_01 /  body_size_02)-1) < RATE_NEN_01_02:
            print("râu nến đang check không lớn hơn 1.25 nến trước đó!")
            return None
        return {
            "open_time": datetime.fromtimestamp(candle_01[0] / 1000).replace(tzinfo=ZoneInfo("UTC")),
            "open": float(candle_01[1]),
            "high": float(candle_01[2]),
            "low": float(candle_01[3]),
            "close": float(candle_01[4])
        }
    except Exception as e:
        print(f"Lỗi lấy nến {symbol_config['symbol']}: {e}")
        return None

def analyze_candle(candle):
    try:
        open_price = candle["open"]
        high_price = candle["high"]
        low_price = candle["low"]
        close_price = candle["close"]

        upper = high_price - max(open_price, close_price)
        upper_percent = (upper / max(open_price, close_price)) * 100 if max(open_price, close_price) > 0 else 0

        lower = min(open_price, close_price) - low_price
        lower_percent = (lower / low_price) * 100 if low_price > 0 else 0

        candle_type = "other"
        if lower_percent >= RATE_PERCENT and lower / (high_price - low_price) >= RATE_BODY:
            candle_type = "Râu nến dưới"
        elif upper_percent >= RATE_PERCENT and upper / (high_price - low_price) >= RATE_BODY:
            candle_type = "Râu nến trên"

        return {
            "candle_type": candle_type,
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "upper_wick_percent": round(upper_percent, 2),
            "lower_wick_percent": round(lower_percent, 2),
            "trend_direction": "LONG" if candle_type == "Râu nến dưới" else "SHORT" if candle_type == "Râu nến trên" else "-"
        }
    except Exception as e:
        send_telegram_alert(f"Lỗi phân tích nến:\n```{str(e)}```", is_critical=True)
        return None

def send_telegram_notification(symbol, candle, analysis):
    if analysis["candle_type"] == "other":
        return

    msg = f"""
📊 *{symbol} - Nến {analysis['candle_type'].upper()}* lúc {datetime.now(VIETNAM_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')}
━━━━━━━━━━━━━━
📈 Open: {analysis['open']:.8f}
📉 Close: {analysis['close']:.8f}
🔺 High: {analysis['high']:.8f}
🔻 Low: {analysis['low']:.8f}
━━━━━━━━━━━━━━
🔼 Râu trên: {analysis['upper_wick_percent']:.4f}%
🔽 Râu dưới: {analysis['lower_wick_percent']:.4f}%
🎯 Long/Short?: {analysis['trend_direction']}"""

    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": msg,
                "parse_mode": "Markdown"
            },
            timeout=10
        )
    except Exception as e:
        print(f"❌ Telegram error: {e}")

def main():
    print("🟢 Bot đang chạy...")
    send_telegram_alert(f"Start server 10 coin", is_critical=False)

    while True:
        try:
            now_utc = datetime.utcnow().replace(tzinfo=ZoneInfo("UTC"))

            if now_utc.minute % 15 == 0 and now_utc.second < 20:
                print(f"\n⏱ Kiểm tra lúc {datetime.now(VIETNAM_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')}")
                for sym in SYMBOLS:
                    candle = fetch_latest_candle(sym)
                    if not candle:
                        continue
                    analysis = analyze_candle(candle)
                    if analysis:
                        print(f"✔️ {sym['symbol']} | {analysis['candle_type']} | Râu nến trên: {analysis['upper_wick_percent']:.4f}% | Râu nến dưới: {analysis['lower_wick_percent']:.4f}%")
                        send_telegram_notification(sym['symbol'], candle, analysis)

                time.sleep(900 - now_utc.second % 60)  # Đợi hết 15 phút tránh trùng
            else:
                time.sleep(1)
        except Exception as e:
            error_msg = f"LỖI VÒNG LẶP:\n{e}\n{traceback.format_exc()}"
            print(error_msg)
            send_telegram_alert(f"```{error_msg}```", is_critical=True)
            time.sleep(10)

if __name__ == "__main__":
    main()
