from django.http import JsonResponse
from datetime import datetime, timedelta
import requests
import pandas as pd
from core.models import Symbol
from backtestingV2.models import HistoricalMarketDataPoint
from backtestingV2.utils.historical_indicators import calculate_all_historical_indicators
from backtestingV2.utils.save_utils import save_indicators_from_df
from backtestingV2.backtest_runner import run_backtest

# 🧠 Mapeo de segundos a formato tipo estrategia
TIMEFRAME_MAP = {
    "60": "1m",
    "300": "5m",
    "900": "15m",
    "1800": "30m",
    "3600": "1h",
    "86400": "1D"
}

def download_historical_data(request):
    symbol_str = request.GET.get("symbol")
    from_date = request.GET.get("from")
    to_date = request.GET.get("to")
    timeframe = request.GET.get("timeframe", "900")

    if not symbol_str or not from_date or not to_date:
        return JsonResponse({"error": "Missing parameters"}, status=400)

    try:
        granularity = int(timeframe)
    except:
        return JsonResponse({"error": "Invalid timeframe"}, status=400)

    # ✅ Convertir a formato esperado por las estrategias
    tf_str = TIMEFRAME_MAP.get(str(granularity), f"{int(granularity) // 60}m")

    product_id = symbol_str.replace("/", "-").replace("_", "-").upper()
    symbol_clean = product_id.replace("-", "")
    try:
        symbol_obj = Symbol.objects.get(symbol=symbol_clean)
    except Symbol.DoesNotExist:
        return JsonResponse({"error": f"Símbolo '{symbol_clean}' no existe en DB"}, status=404)

    start = datetime.strptime(from_date, "%Y-%m-%d")
    end = datetime.strptime(to_date, "%Y-%m-%d")
    delta = timedelta(days=30)
    cursor = start
    all_rows = []

    while cursor < end:
        chunk_end = min(cursor + delta, end)
        url = f"https://api.exchange.coinbase.com/products/{product_id}/candles"
        params = {
            "start": cursor.isoformat(),
            "end": chunk_end.isoformat(),
            "granularity": granularity
        }

        try:
            print(f"📡 Fetching: {url} | {cursor.date()} → {chunk_end.date()}")
            r = requests.get(url, params=params, timeout=15)
            r.raise_for_status()
        except requests.exceptions.ReadTimeout:
            return JsonResponse({"error": "⏳ Timeout al conectar con Coinbase. Intenta con un rango menor."}, status=504)
        except requests.exceptions.RequestException as e:
            return JsonResponse({"error": f"❌ Error de red: {str(e)}"}, status=500)

        candles = r.json()
        for c in candles:
            t, low, high, open_, close, volume = c
            start_time = datetime.utcfromtimestamp(t)
            end_time = start_time + timedelta(seconds=granularity)
            HistoricalMarketDataPoint.objects.get_or_create(
                symbol=symbol_obj,
                timeframe=tf_str,  # ✅ Ya no es "900s", es "15m"
                start_time=start_time,
                defaults={
                    "open": open_,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": volume,
                    "end_time": end_time,
                    "source": "coinbase_rest"
                }
            )
            all_rows.append({
                "time": start_time,
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume
            })

        cursor = chunk_end

    if not all_rows:
        return JsonResponse({"error": "No se obtuvieron datos históricos para ese rango."}, status=404)

    # 📈 Calcular indicadores
    df = pd.DataFrame(sorted(all_rows, key=lambda x: x["time"]))
    df = calculate_all_historical_indicators(df)
    save_indicators_from_df(df, symbol_obj, tf_str)  # ✅ usar el mismo tf

    return JsonResponse({"message": f"{len(df)} puntos e indicadores procesados para {symbol_str}."})


def run_backtest_view(request):
    symbol = request.GET.get("symbol")
    from_date = request.GET.get("from")
    to_date = request.GET.get("to")
    timeframe = request.GET.get("timeframe", "900")
    capital = float(request.GET.get("capital", 10000))

    if not symbol or not from_date or not to_date:
        return JsonResponse({"error": "Parámetros incompletos"}, status=400)

    run_backtest(
        symbol_str=symbol.replace("-", ""),
        from_date=datetime.strptime(from_date, "%Y-%m-%d"),
        to_date=datetime.strptime(to_date, "%Y-%m-%d"),
        timeframe=TIMEFRAME_MAP.get(str(timeframe), f"{int(timeframe) // 60}m"),  # ✅ usar formato correcto
        capital=capital,
    )

    return JsonResponse({"message": f"✅ Backtest completado para {symbol}."})
