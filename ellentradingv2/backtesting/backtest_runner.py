from collections import defaultdict
from datetime import datetime
from core.models.symbol import Symbol
from backtesting.models import HistoricalMarketDataPoint
from strategies.models import OpenStrategy
from risk.risk_manager import RiskManager
from django.utils.timezone import timedelta
from collections import Counter
from strategies.base.factory import get_entry_strategy

class BacktestRunner:
    def __init__(self, symbol: Symbol, initial_balance: float, strategies: list[OpenStrategy], start_date: datetime, end_date: datetime):
        self.symbol = symbol
        self.initial_balance = initial_balance
        self.strategies = strategies
        self.start_date = start_date
        self.end_date = end_date
        self.signals = []
        self.trades = []

    def is_trade_invalid_due_to_overlap(self, signal):
        from core.utils.time import normalize_timestamp_by_timeframe

        candle_time = normalize_timestamp_by_timeframe(signal.timestamp, signal.timeframe)

        for t in self.trades:
            if not hasattr(t, "timestamp") or not hasattr(t, "strategy"):
                continue

            t_time = normalize_timestamp_by_timeframe(t.timestamp, signal.timeframe)

            # Rechazar si ya hay trade en misma vela, misma estrategia y dirección
            if (
                    t.symbol == signal.symbol and
                    t_time == candle_time and
                    t.strategy == signal.strategy.name and
                    t.direction.lower() == signal.signal.lower()
            ):
                return True

            # ⚠️ Rechazar si timestamp es menor que el último cierre
            if hasattr(t, "closed_at") and signal.timestamp < t.closed_at:
                return True

        return False

    def run(self):
        strategies_by_timeframe = defaultdict(list)
        for strat in self.strategies:
            strategies_by_timeframe[strat.timeframe].append(strat)

        for timeframe, strategy_list in strategies_by_timeframe.items():
            candles = HistoricalMarketDataPoint.objects.select_related("indicators").filter(
                symbol=self.symbol.symbol,
                timeframe=timeframe,
                timestamp__range=(self.start_date, self.end_date)
            ).order_by("timestamp")

            print(f"📊 Cargando {len(candles)} velas para {self.symbol.symbol} en timeframe {timeframe}")

            for i in range(len(candles)):
                window = candles[:i + 1]
                if not window:
                    continue

                current_candle = window[-1]
                current_time = current_candle.timestamp
                signals_this_bar = []

                for strategy_instance in strategy_list:
                    strategy = get_entry_strategy(strategy_instance.name.lower().replace(" strategy", "").replace(" ", "_"))

                    if not strategy:
                        continue

                    strategy.strategy_instance = strategy_instance
                    strategy.timeframe = strategy_instance.timeframe
                    strategy.required_bars = strategy_instance.required_bars

                    if len(window) < strategy.required_bars:
                        continue

                    signal = strategy.should_generate_signal(
                        self.symbol,
                        execution_mode="backtest",
                        candles=window
                    )
                    if signal:
                        print(f"✅ Señal generada por {strategy_instance.name} @ {current_time} → {signal.signal}")
                        signal.timestamp = current_time
                        signal.market_data = current_candle
                        signal.strategy = strategy_instance
                        signal.timeframe = strategy_instance.timeframe
                        signal.is_from_backtest = True

                        # 🔥 Inyectar .symbol como si fuera una relación real
                        from types import SimpleNamespace

                        from core.models.symbol import Symbol
                        signal.symbol = Symbol.objects.get(symbol=current_candle.symbol)

                if signals_this_bar:
                    self.signals.extend(signals_this_bar)

                    # ✅ RiskManager sobre todas las señales actuales
                    rm = RiskManager(self.symbol.symbol, execution_mode="backtest", capital=self.initial_balance)
                    rm.signals = [
                        s for s in self.signals
                        if s.symbol.symbol == self.symbol.symbol and
                           s.timeframe == timeframe and
                           s.timestamp >= current_time - timedelta(minutes=15) and
                           s.timestamp <= current_time
                    ]

                    trade = rm.analyze_and_execute(price=current_candle.close, current_time=current_time)
                    if trade:
                        future_candles = candles[i + 1:]
                        from backtesting.strategies.backtest_watcher import BacktestWatcher
                        watcher = BacktestWatcher(trade, future_candles)
                        result = watcher.simulate()

                        trade.exit_price = result["exit_price"]
                        trade.closed_at = result["exit_time"]
                        trade.pnl = (result["exit_price"] - trade.price) * trade.quantity if not trade.notional else \
                            ((result["exit_price"] / trade.price) - 1) * trade.notional
                        trade.notes = result["reason"]

                        self.initial_balance += trade.pnl
                        self.trades.append(trade)

        reasons = Counter()
        for trade in self.trades:
            reason = getattr(trade, "notes", "Unknown")
            reasons[reason] += 1

        print("📋 Motivos de cierre:")
        for reason, count in reasons.items():
            print(f"   • {reason}: {count}")



        return self.signals, self.trades
