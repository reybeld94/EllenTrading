from backtesting.models.HistoricalSignal import Signal
from core.models import OpenStrategy

# Lista de nombres definidos en backtest_strategy_runner
STRATEGIAS_IMPLEMENTADAS = [
    "MACD Crossover Strategy",
    "RSI Breakout Strategy",
    "Ichimoku Cloud Breakout",
    "ADX Trend Strength Strategy",
    "Bollinger Band Breakout",
    "Donchian Channel Breakout",
    "Volume Spike Breakout Strategy",
    "Bullish Engulfing Pattern",
    "Bearish Engulfing Pattern",
    "Moving Average Cross Strategy",
    "Stochastic Oscillator Strategy",
    "Parabolic SAR Trend Strategy",
    "CCI Extreme Strategy",
]

def estrategias_sin_senales():
    estrategias = OpenStrategy.objects.filter(name__in=STRATEGIAS_IMPLEMENTADAS)
    sin_senales = []

    for estrategia in estrategias:
        if not Signal.objects.filter(strategy=estrategia).exists():
            sin_senales.append(estrategia.name)

    print("📉 Estrategias sin señales guardadas en HistoricalSignal:")
    for nombre in sin_senales:
        print(f"❌ {nombre}")

    if not sin_senales:
        print("✅ Todas las estrategias tienen señales registradas.")

# Llamada al script (puedes ponerla en un comando o view)
estrategias_sin_senales()


from core.models import OpenStrategy
from backtesting.models.HistoricalMarketDataPoint import HistoricalMarketDataPoint
from backtesting.models.HistoricalSignal import Signal
from backtesting.strategies.backtesting_factory import build_backtest_strategy

from collections import defaultdict

def run_full_backtest(symbol_code="AAPL"):
    estrategias = OpenStrategy.objects.all()
    conteo = defaultdict(int)

    print(f"🧠 Cargando velas históricas para {symbol_code}...")
    all_candles = list(HistoricalMarketDataPoint.objects.filter(symbol=symbol_code).select_related("indicators").order_by("timestamp"))

    for estrategia_inst in estrategias:
        print(f"\n🔍 Evaluando estrategia: {estrategia_inst.name}")
        estrategia = build_backtest_strategy(estrategia_inst)
        tf = estrategia.timeframe
        filtered = [c for c in all_candles if c.timeframe == tf]

        if len(filtered) < estrategia.required_bars + 1:
            print(f"⛔ No hay suficientes velas para {tf}")
            continue

        for i in range(estrategia.required_bars, len(filtered)):
            ventana = filtered[i - estrategia.required_bars:i]
            estrategia.set_candles(ventana)
            signal = estrategia.should_generate_signal(symbol_code)

            if signal:
                conteo[estrategia_inst.name] += 1
                print(f"✅ {estrategia_inst.name} — {signal.signal.upper()} @ {signal.timestamp.date()} conf={signal.confidence_score}")

    print("\n📊 RESUMEN FINAL:")
    for nombre, cantidad in conteo.items():
        print(f"📈 {nombre}: {cantidad} señales")

    estrategias_sin = [e.name for e in estrategias if conteo[e.name] == 0]
    if estrategias_sin:
        print("\n⚠️ Estrategias SIN NINGUNA señal:")
        for nombre in estrategias_sin:
            print(f"❌ {nombre}")

# Ejecutar
run_full_backtest("AAPL")  # o BTCUSD, ETHUSD, etc
