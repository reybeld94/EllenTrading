import os
from datetime import datetime, timedelta
import pandas as pd
from django.db import transaction
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from backtesting.models import HistoricalMarketDataPoint

# API Keys
API_KEY = "PKALPV6774BZYC8TQ29Q"
API_SECRET = "tUczQ1yDfIQMQzXubtwmpBFiJj8JNZhkMc8gYQaT"

client = StockHistoricalDataClient(API_KEY, API_SECRET)

# 📈 Configuración
SYMBOL = "AAPL"
END_DATE = datetime.now()
MIN_DATE = datetime(2022, 5, 1)

# ⏱ Timeframes a descargar
TIMEFRAMES = {
    "1h": TimeFrame(1, TimeFrameUnit.Hour),
    "15m": TimeFrame(15, TimeFrameUnit.Minute),
    "5m": TimeFrame(5, TimeFrameUnit.Minute),
}

def fetch_block(symbol: str, tf_str: str, timeframe, start_date: datetime, end_date: datetime):
    print(f"📥 Descargando {symbol} [{tf_str}] del {start_date.date()} al {end_date.date()}")

    request_params = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=timeframe,
        start=start_date,
        end=end_date,
    )

    bars = client.get_stock_bars(request_params)

    if bars.df.empty:
        print("⚠️ No se recibieron datos.")
        return

    df = bars.df.reset_index()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["timestamp"] = df["timestamp"].dt.tz_convert("UTC")

    timestamps = set(
        HistoricalMarketDataPoint.objects.filter(
            symbol=symbol,
            timeframe=tf_str,
            timestamp__in=df["timestamp"]
        ).values_list("timestamp", flat=True)
    )

    nuevos = []
    for _, row in df.iterrows():
        if row["timestamp"] in timestamps:
            continue

        nuevos.append(HistoricalMarketDataPoint(
            symbol=row["symbol"],
            timeframe=tf_str,
            timestamp=row["timestamp"],
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
            volume=row["volume"],
            source="alpaca"
        ))

    if nuevos:
        with transaction.atomic():
            HistoricalMarketDataPoint.objects.bulk_create(nuevos, batch_size=1000)
        print(f"✅ Guardadas {len(nuevos)} velas nuevas para {symbol} [{tf_str}]")
    else:
        print(f"✅ No había nuevas velas para {symbol} [{tf_str}].")

def run():
    current_end = END_DATE
    while current_end > MIN_DATE:
        current_start = current_end - timedelta(days=90)
        for tf_str, timeframe in TIMEFRAMES.items():
            fetch_block(SYMBOL, tf_str, timeframe, current_start, current_end)
        current_end = current_start  # move to next block back in time

if __name__ == "__main__":
    run()