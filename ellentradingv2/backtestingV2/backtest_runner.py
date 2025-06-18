# backtestingV2/backtest_runner.py

from datetime import datetime
from core.models import Symbol
from backtestingV2.models import HistoricalMarketDataPoint, HistoricalTrade
from strategies.models import OpenStrategy
from risk.risk_manager import RiskManager

def run_backtest(symbol_str, from_date, to_date, timeframe, capital):
    """
    Corre un backtest completo sin guardar señales, solo trades.
    """

    try:
        symbol = Symbol.objects.get(symbol=symbol_str.replace("-", ""))
    except Symbol.DoesNotExist:
        print(f"❌ Símbolo {symbol_str} no encontrado en DB.")
        return

    bars = HistoricalMarketDataPoint.objects.filter(
        symbol=symbol,
        timeframe=timeframe,
        start_time__gte=from_date,
        start_time__lte=to_date
    ).order_by("start_time")

    print(f"📊 Backtest: {symbol_str} desde {from_date} hasta {to_date} ({len(bars)} velas)")

    trades = []

    for bar in bars:
        # 🧠 1. Ejecutar estrategias activas (modo backtest)
        generated_signals = []
        for strategy in OpenStrategy.objects.filter(execution_mode="backtest"):
            try:
                signal = strategy.should_generate_signal(bar)
                if signal:
                    generated_signals.append(signal)  # Solo en memoria
            except Exception as e:
                print(f"⚠️ Error en {strategy.name}: {e}")

        # 🧠 2. Usar RiskManager en modo backtest
        rm = RiskManager(symbol.symbol, execution_mode="backtest", capital=capital)
        rm.signals = generated_signals  # Inyectamos señales directamente
        trade = rm.analyze_and_execute(price=bar.close, current_time=bar.start_time, verbose=False)

        if trade:
            print(f"✅ Trade {trade.direction} @ {bar.start_time.date()} from {trade.strategy}")
            t = HistoricalTrade.objects.create(
                symbol=symbol,
                direction=trade.direction,
                price=trade.price,
                quantity=trade.quantity,
                notional=trade.notional,
                stop_loss=trade.stop_loss,
                take_profit=trade.take_profit,
                trailing_stop=trade.trailing_stop,
                trailing_level=trade.trailing_level,
                execution_mode="backtest",
                status="EXECUTED",
                confidence_score=trade.confidence_score if hasattr(trade, "confidence_score") else 0,
                strategy=trade.strategy,
                executed_at=bar.start_time
            )
            trades.append(t)

    print(f"🏁 Backtest terminado: {len(trades)} trades ejecutados.")
