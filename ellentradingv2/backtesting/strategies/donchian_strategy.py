from backtesting.strategies.BacktestStrategy import BacktestStrategy
from backtesting.models.HistoricalSignal import Signal
from core.models.enums import SignalType

class DonchianBacktestStrategy(BacktestStrategy):
    name = "Donchian Channel Breakout"

    def should_generate_signal(self, symbol):
        candles = [
            c for c in self.candles
            if c.indicators and c.indicators.donchian_upper is not None and c.indicators.donchian_lower is not None
        ]
        if len(candles) < 1:
            return None

        last = candles[-1]
        upper = last.indicators.donchian_upper
        lower = last.indicators.donchian_lower
        middle = (upper + lower) / 2 if upper is not None and lower is not None else None
        price = last.close

        if upper is None or lower is None or middle is None:
            return None

        signal_type = None
        confidence = 50

        if price > upper:
            signal_type = SignalType.BUY
        elif price < lower:
            signal_type = SignalType.SELL
        else:
            return None  # No rompió nada

        # Bonus de confianza por distancia al canal medio
        distance = abs(price - middle) / (upper - lower) if (upper - lower) != 0 else 0
        if distance > 0.5:
            confidence += 10
        if distance > 0.8:
            confidence += 10

        confidence = min(confidence, 100)
        if confidence < 70:
            return None

        return Signal(
            signal=signal_type,
            confidence_score=confidence,
            timestamp=last.timestamp,
            timeframe=self.timeframe,
            market_data=last,
            strategy=self.strategy_instance,
            is_from_backtest=True
        )
