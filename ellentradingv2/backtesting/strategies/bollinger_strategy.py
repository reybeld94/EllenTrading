from backtesting.strategies.BacktestStrategy import BacktestStrategy
from backtesting.models.HistoricalSignal import Signal
from core.models.enums import SignalType

class BollingerBacktestStrategy(BacktestStrategy):
    name = "Bollinger Band Breakout"

    def should_generate_signal(self, symbol):
        candles = [
            c for c in self.candles
            if c.indicators and all([
                c.indicators.bollinger_upper is not None,
                c.indicators.bollinger_middle is not None,
                c.indicators.bollinger_lower is not None
            ])
        ]

        if len(candles) < 1:
            return None

        last = candles[-1]
        price = last.close
        upper = last.indicators.bollinger_upper
        lower = last.indicators.bollinger_lower
        middle = last.indicators.bollinger_middle

        if None in (upper, lower, middle):
            return None

        signal_type = None
        confidence = 50

        if price > upper:
            signal_type = SignalType.SELL
        elif price < lower:
            signal_type = SignalType.BUY
        else:
            return None  # No rompió ninguna banda

        # Bonus si el precio se aleja bastante del centro
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
