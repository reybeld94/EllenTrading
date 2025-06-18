import os
import time
import pandas as pd
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware, is_aware

from alpaca.data.historical import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from django.utils.timezone import now as dj_now


from core.models import Symbol, MarketDataPoint
from core.models.livetechnicalindicator import LiveTechnicalIndicator
from backtesting.indicators import calculate_all_indicators
from strategies.strategies.runner import run_entry_strategies

crypto_client = CryptoHistoricalDataClient()

TIMEFRAMES = {
    "5m": (TimeFrame(5, TimeFrameUnit.Minute), 5),
    "15m": (TimeFrame(15, TimeFrameUnit.Minute), 15),
    "1h": (TimeFrame(1, TimeFrameUnit.Hour), 60),
}



# ✅ Lista de símbolos con /
ENABLED_SYMBOLS = [
    "BTC/USD",
    "ETH/USD",
    "SOL/USD",
    "DOGE/USD",
    "LINK/USD",
    "TRX/USD",
    "XLM/USD",
    "USDT/USD",
]

def is_crypto(symbol_str):
    return symbol_str.upper().endswith("/USD")

last_call = {}  # {(symbol, timeframe): datetime}

class Command(BaseCommand):
    help = "Inicia el agregador de velas cripto (5m / 15m / 1h) desde Alpaca."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("📡 Iniciando agregador de velas cripto (5m / 15m / 1h)..."))
        self._load_initial_candles()

        while True:
            now = dj_now()

            for symbol_str in ENABLED_SYMBOLS:
                symbol_code = symbol_str.replace("/", "")
                try:
                    symbol = Symbol.objects.get(symbol=symbol_code)
                except Symbol.DoesNotExist:
                    self.stderr.write(f"⚠️ Symbol '{symbol_code}' no existe en la base de datos.")
                    continue

                for tf_str, (tf_obj, tf_minutes) in TIMEFRAMES.items():
                    key = (symbol.symbol, tf_str)

                    # Verifica si ya se actualizó recientemente
                    if key in last_call and (now - last_call[key] < timedelta(minutes=tf_minutes)):
                        continue

                    try:
                        # Obtiene la última vela guardada
                        last_bar = MarketDataPoint.objects.filter(
                            symbol=symbol,
                            timeframe=tf_str
                        ).order_by("-start_time").first()

                        if last_bar:
                            start_time = last_bar.start_time + timedelta(minutes=tf_minutes)
                        else:
                            start_time = now - timedelta(minutes=tf_minutes * 50)  # carga inicial

                        end_time = datetime.utcnow()

                        # Asegura que ambos timestamps tengan timezone
                        if not is_aware(start_time):
                            start_time = make_aware(start_time)
                        if not is_aware(end_time):
                            end_time = make_aware(end_time)

                        if start_time >= end_time:
                            continue  # ⛔ evita rangos inválidos

                        req = CryptoBarsRequest(
                            symbol_or_symbols=symbol_str,
                            start=start_time,
                            end=end_time,
                            timeframe=tf_obj
                        )

                        df = crypto_client.get_crypto_bars(req).df
                        df = df[df.index.get_level_values(0) == symbol_str]
                        df = df.reset_index()

                        for _, row in df.iterrows():
                            ts = row["timestamp"].to_pydatetime()
                            if not is_aware(ts):
                                ts = make_aware(ts)

                            obj, created = MarketDataPoint.objects.update_or_create(
                                symbol=symbol,
                                timeframe=tf_str,
                                start_time=ts,
                                defaults={
                                    "open": row.open,
                                    "high": row.high,
                                    "low": row.low,
                                    "close": row.close,
                                    "volume": row.volume,
                                    "normalized_volume": row.volume,
                                    "vwap": getattr(row, "vwap", None),
                                    "trade_count": getattr(row, "trade_count", None),
                                    "exchange": getattr(row, "exchange", None),
                                    "end_time": ts + timedelta(minutes=tf_minutes),
                                    "is_closed": True,
                                    "source": "historical_live"
                                }
                            )

                            if created:
                                self.stdout.write(f"🆕 Vela nueva {symbol.symbol} [{tf_str}] @ {ts}")
                                self._calculate_indicators(symbol, tf_str)
                                run_entry_strategies(symbol)

                        last_call[key] = dj_now()


                    except Exception as e:
                        self.stderr.write(f"❌ Error {symbol.symbol} [{tf_str}]: {e}")

            time.sleep(60)

    def _load_initial_candles(self):
        if os.path.exists("initial_candles.lock"):
            self.stdout.write("⏩ Velas históricas ya cargadas (lock file detectado).")
            return

        self.stdout.write("🚀 Cargando velas históricas (últimas 48h)...")


        now = dj_now()

        start = now - timedelta(hours=48)

        for symbol_str in ENABLED_SYMBOLS:
            symbol_code = symbol_str.replace("/", "")
            try:
                symbol = Symbol.objects.get(symbol=symbol_code)
            except Symbol.DoesNotExist:
                self.stderr.write(f"⚠️ Symbol '{symbol_code}' no existe en la base de datos.")
                continue

            for tf_str, (tf_obj, _) in TIMEFRAMES.items():
                try:
                    req = CryptoBarsRequest(
                        symbol_or_symbols=symbol_str,
                        start=start,
                        end=now,
                        timeframe=tf_obj
                    )
                    df = crypto_client.get_crypto_bars(req).df
                    df = df[df.index.get_level_values(0) == symbol_str]
                    df = df.reset_index()

                    for _, row in df.iterrows():
                        ts = row["timestamp"].to_pydatetime()
                        if not is_aware(ts):
                            ts = make_aware(ts)
                        tf_minutes = {
                            "5m": 5,
                            "15m": 15,
                            "1h": 60,
                        }.get(tf_str, 5)
                        MarketDataPoint.objects.update_or_create(
                            symbol=symbol,
                            timeframe=tf_str,
                            start_time=ts,
                            defaults={
                                "open": row.open,
                                "high": row.high,
                                "low": row.low,
                                "close": row.close,
                                "volume": row.volume,
                                "normalized_volume": row.volume,
                                "vwap": getattr(row, "vwap", None),
                                "trade_count": getattr(row, "trade_count", None),
                                "exchange": getattr(row, "exchange", None),
                                "end_time": ts + timedelta(minutes=tf_minutes),
                                "is_closed": True,
                                "source": "historical_api"
                            }
                        )

                    self._calculate_indicators(symbol, tf_str)
                    run_entry_strategies(symbol)
                    self.stdout.write(f"✅ {symbol.symbol} [{tf_str}] cargado.")

                except Exception as e:
                    self.stderr.write(f"❌ Error inicial {symbol.symbol} [{tf_str}]: {e}")

        with open("initial_candles.lock", "w") as f:
            f.write("done")
        self.stdout.write("✅ Carga inicial completada.\n")

    def _calculate_indicators(self, symbol, tf_str):
        latest = MarketDataPoint.objects.filter(
            symbol=symbol,
            timeframe=tf_str
        ).order_by("-start_time")[:50]

        bars = list(latest)[::-1]
        df = pd.DataFrame([{
            "timestamp": b.start_time,
            "open": b.open,
            "high": b.high,
            "low": b.low,
            "close": b.close,
            "volume": b.volume,
        } for b in bars])

        df = calculate_all_indicators(df)
        df = df.reset_index(drop=True)

        for bar, row in zip(bars, df.to_dict(orient="records")):
            allowed = {f.name for f in LiveTechnicalIndicator._meta.fields if f.name not in ["id", "market_data"]}
            data = {k: row[k] for k in row if k in allowed}
            LiveTechnicalIndicator.objects.update_or_create(
                market_data=bar,
                defaults=data
            )
