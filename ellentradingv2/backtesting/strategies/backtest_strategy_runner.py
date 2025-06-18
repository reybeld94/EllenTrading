from backtesting.models.HistoricalSignal import Signal
from backtesting.models.HistoricalMarketDataPoint import HistoricalMarketDataPoint
from backtesting.strategies.backtesting_factory import build_backtest_strategy
from core.models import OpenStrategy
from collections import defaultdict

# SOLO estas están implementadas
STRATEGIES_IMPLEMENTADAS = [
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


def run_entry_strategies(symbol_code="AAPL", verbose=True):
    estrategias = OpenStrategy.objects.filter(name__in=STRATEGIES_IMPLEMENTADAS)
    conteo = defaultdict(int)

    if verbose:
        print(f"🚀 Iniciando backtest completo para {symbol_code}...\n")

    # Cargar todas las velas del símbolo
    all_candles = list(
        HistoricalMarketDataPoint.objects
        .filter(symbol=symbol_code)
        .select_related("indicators")
        .order_by("timestamp")
    )

    for estrategia_inst in estrategias:
        try:
            estrategia = build_backtest_strategy(estrategia_inst)
        except Exception as e:
            if verbose:
                print(f"⚠️ Ignorada: {estrategia_inst.name} — {e}")
            continue

        tf = estrategia.timeframe
        required = estrategia.required_bars

        velas_tf = [c for c in all_candles if c.timeframe == tf]

        if len(velas_tf) < required:
            if verbose:
                print(f"⏭️ {estrategia.name} — Insuficientes velas para {tf}")
            continue

        if verbose:
            print(f"📈 Ejecutando {estrategia.name} ({tf}) con {len(velas_tf)} velas...")

        for i in range(required, len(velas_tf)):
            ventana = velas_tf[i - required:i]
            estrategia.set_candles(ventana)
            signal = estrategia.should_generate_signal(symbol_code)

            if signal:
                conteo[estrategia.name] += 1

                _, created = Signal.objects.get_or_create(
                    strategy=estrategia_inst,
                    signal=signal.signal,
                    timestamp=signal.timestamp,
                    market_data=signal.market_data,
                    defaults={
                        'confidence_score': signal.confidence_score,
                        'is_from_backtest': True,
                        'timeframe': signal.timeframe
                    }
                )



    # Resumen
    if verbose:
        print("\n📊 RESUMEN FINAL DE SEÑALES:")
        for nombre, cantidad in conteo.items():
            print(f"📌 {nombre}: {cantidad} señales")

        sin_señales = [e.name for e in estrategias if conteo[e.name] == 0]
        if sin_señales:
            print("\n⚠️ Estrategias SIN NINGUNA señal:")
            for nombre in sin_señales:
                print(f"❌ {nombre}")

    print("\n🏁 Backtest completado.\n")
