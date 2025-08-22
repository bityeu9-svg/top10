import requests
from datetime import datetime
from zoneinfo import ZoneInfo
import time
import traceback
# ========== CẤU HÌNH ==========
VIETNAM_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")
TELEGRAM_BOT_TOKEN = "8226246719:AAHXDggFiFYpsgcq1vwTAWv7Gsz1URP4KEU"
TELEGRAM_CHAT_ID = "-4706073326"
RATE_PERCENT_TOP = 0.4
RATE_PERCENT_MID = 0.68
RATE_PERCENT_LOW = 0.8
RATE_BODY = 0.5
CHART_TYPE = "15m"
# Danh sách coin cố định
SYMBOLS = [
    {"symbol": s, "candle_interval": CHART_TYPE, "limit": 2}
    for s in [
        "BTCUSDT", "ETHUSDT", "SOLUSDT",
        "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "TRXUSDT", "TONUSDT",
        "LINKUSDT", "MATICUSDT", "DOTUSDT", "LTCUSDT",
        "AVAXUSDT", "UNIUSDT", "BCHUSDT", "ETCUSDT", "XLMUSDT",
        "ATOMUSDT", "XMRUSDT", "APTUSDT", "FILUSDT", "HBARUSDT",
        "VETUSDT", "NEARUSDT", "INJUSDT", "OPUSDT", "SUIUSDT",
        # Thêm các đồng coin phổ biến khác trên Binance
        "CRVUSDT", "ARKMUSDT", "JASMYUSDT", "WIFUSDT", "TIAUSDT",
        "ORDIUSDT", "1000PEPEUSDT", "SEIUSDT", "BLURUSDT", "MEMEUSDT",
        "STXUSDT", "SSVUSDT", "LDOUSDT", "DYDXUSDT", "GMXUSDT",
        "AGIXUSDT", "FETUSDT", "GALAUSDT", "SANDUSDT", "APEUSDT"
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
        data = response.json()
        # Lấy nến đã đóng cửa gần nhất và nến hiện tại
        closed_candle = data[-2]
        current_candle = data[-1]
        def parse_candle(candle):
            return {
                "open_time": datetime.fromtimestamp(candle[0] / 1000).replace(tzinfo=ZoneInfo("UTC")),
                "open": float(candle[1]),
                "high": float(candle[2]),
                "low": float(candle[3]),
                "close": float(candle[4]),
                "symbol": symbol_config["symbol"]
            }
        return [parse_candle(closed_candle), parse_candle(current_candle)]
    except Exception as e:
        print(f"Lỗi lấy nến {symbol_config['symbol']}: {e}")
        return None

def analyze_candle(candle):
    try:
        open_price = candle["open"]
        high_price = candle["high"]
        low_price = candle["low"]
        close_price = candle["close"]
        print(f"Phân tích nến {candle['symbol']} - Open: {open_price}, High: {high_price}, Low: {low_price}, Close: {close_price}")

        upper = high_price - max(open_price, close_price)
        upper_percent = (upper / max(open_price, close_price)) * 100 if max(open_price, close_price) > 0 else 0
        print(f"Râu nến trên: {upper_percent:.4f}%")

        lower = min(open_price, close_price) - low_price
        lower_percent = (lower / low_price) * 100 if low_price > 0 else 0 and close_price < open_price
        print(f"Râu nến dưới: {lower_percent:.4f}%")

        # Xác định ngưỡng phần trăm râu nến theo cặp
        current_symbol = candle.get("symbol") if "symbol" in candle else None
        # Phân nhóm coin để chọn ngưỡng wick_percent_threshold
        COINS_TOP = {"BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"}
        COINS_MID = {
            "XRPUSDT", "ADAUSDT", "DOGEUSDT", "TRXUSDT", "TONUSDT",
            "LINKUSDT", "MATICUSDT", "DOTUSDT", "LTCUSDT",
            "AVAXUSDT", "UNIUSDT", "BCHUSDT", "ETCUSDT", "XLMUSDT",
            "ATOMUSDT", "XMRUSDT", "APTUSDT", "FILUSDT", "HBARUSDT",
            "VETUSDT", "NEARUSDT", "INJUSDT", "OPUSDT", "SUIUSDT"
        }
        if current_symbol in COINS_TOP:
            wick_percent_threshold = RATE_PERCENT_TOP
        elif current_symbol in COINS_MID:
            wick_percent_threshold = RATE_PERCENT_MID
        else:
            wick_percent_threshold = RATE_PERCENT_LOW

        candle_type = "other"
        # Râu nến dưới dài, râu trên < 0.1%
        if (
            lower_percent >= wick_percent_threshold
            and lower / (high_price - low_price) >= RATE_BODY
            and close_price > open_price
            and upper_percent < 0.1
        ):
            candle_type = "Râu nến dưới"
        # Râu nến trên dài, râu dưới < 0.1%
        elif (
            upper_percent >= wick_percent_threshold
            and upper / (high_price - low_price) >= RATE_BODY
            and close_price < open_price
            and lower_percent < 0.1
        ):
            candle_type = "Râu nến trên"

        # Xác định hướng xu hướng dựa trên giá đóng/mở
        if candle_type  ==  "Râu nến dưới":
            trend_direction = "Long"
        elif candle_type  ==  "Râu nến trên":
            trend_direction = "Short"
        else:
            trend_direction = "Sideways"

        return {
            "candle_type": candle_type,
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "upper_wick_percent": round(upper_percent, 2),
            "lower_wick_percent": round(lower_percent, 2),
            "trend_direction": trend_direction
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
    send_telegram_alert(f"Start server 30 coin", is_critical=False)
    while True:
        try:
            now_utc = datetime.now(ZoneInfo("UTC"))
            print(f"🕒 Thời gian start: {now_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            # Chạy mỗi 15 phút (có thể điều chỉnh theo nhu cầu)
            if now_utc.minute % 15 == 0 and now_utc.second < 10:
                for sym in SYMBOLS:
                    candles = fetch_latest_candle(sym)
                    if not candles:
                        continue
                    for candle in candles:
                        analysis = analyze_candle(candle)
                        if analysis and analysis["candle_type"] != "other":
                            print(f"✔️ {sym['symbol']} | {analysis['candle_type']} | Râu nến trên: {analysis['upper_wick_percent']:.4f}% | Râu nến dưới: {analysis['lower_wick_percent']:.4f}%")
                            send_telegram_notification(sym['symbol'], candle, analysis)
                # Tính thời gian chờ đến mốc 15 phút tiếp theo
                now_utc = datetime.now(ZoneInfo("UTC"))
                print(f"🕒 trước khi sleep {now_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC")
                time.sleep(900 - now_utc.second-2)
            else:
                time.sleep(1)
            print(f"🕒 Thời gian end: {now_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC")    
        except Exception as e:
            error_msg = f"LỖI VÒNG LẶP:\n{e}\n{traceback.format_exc()}"
            print(error_msg)
            send_telegram_alert(f"```{error_msg}```", is_critical=True)
            time.sleep(10)

if __name__ == "__main__":
    main()
