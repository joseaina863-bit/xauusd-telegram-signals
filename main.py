
import os
import time
import requests
import yfinance as yf
import pandas as pd

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_message(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(
        url,
        data={"chat_id": CHAT_ID, "text": message},
        timeout=20
    )

def analyze():
    data = yf.download(
        "XAUUSD=X",
        period="5d",
        interval="5m",
        progress=False
    )

    if data.empty:
        print("Aucune donnée disponible")
        return None

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    close = data["Close"]
    high = data["High"]
    low = data["Low"]

    ema9 = close.ewm(span=9).mean()
    ema21 = close.ewm(span=21).mean()

    previous_rsi = close.diff()
    gain = previous_rsi.clip(lower=0).ewm(
        alpha=1/14, adjust=False
    ).mean()
    loss = (-previous_rsi.clip(upper=0)).ewm(
        alpha=1/14, adjust=False
    ).mean()
    rsi = 100 - (100 / (1 + gain / loss))

    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)

    atr = tr.rolling(14).mean()

    if len(data) < 30:
        return None

    i = -2
    previous = -3

    price = float(close.iloc[i])
    volatility = float(atr.iloc[i])
    current_rsi = float(rsi.iloc[i])

    if pd.isna(volatility) or volatility <= 0:
        return None

    direction = None

    if (ema9.iloc[previous] <= ema21.iloc[previous]
            and ema9.iloc[i] > ema21.iloc[i]
            and 50 < current_rsi < 70):
        direction = "BUY"

    elif (ema9.iloc[previous] >= ema21.iloc[previous]
            and ema9.iloc[i] < ema21.iloc[i]
            and 30 < current_rsi < 50):
        direction = "SELL"

    if not direction:
        return None

    risk = volatility * 1.5

    if direction == "BUY":
        sl = price - risk
        tp1 = price + risk * 1.5
        tp2 = price + risk * 2
    else:
        sl = price + risk
        tp1 = price - risk * 1.5
        tp2 = price - risk * 2

    return (
        f"XAUUSD - SIGNAL {direction}\n\n"
        f"Timeframe: M5\n"
        f"Entry: {price:.2f}\n"
        f"Stop Loss: {sl:.2f}\n"
        f"Take Profit 1: {tp1:.2f}\n"
        f"Take Profit 2: {tp2:.2f}\n"
        f"RSI: {current_rsi:.1f}\n\n"
        "Signal technique - confirmation nécessaire."
    )

def main():
    if not TOKEN or not CHAT_ID:
        print("BOT_TOKEN ou CHAT_ID manquant")
        return

    last_signal = None

    while True:
        try:
            signal = analyze()

            if signal and signal != last_signal:
                send_message(signal)
                last_signal = signal
                print(signal)

        except Exception as error:
            print("Erreur:", error)

        time.sleep(60)

if __name__ == "__main__":
    main()
