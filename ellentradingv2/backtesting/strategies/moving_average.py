from backtesting.strategies.BacktestStrategy import BacktestStrategy
from backtesting.models.HistoricalSignal import Signal
from core.models.enums import SignalType

class MovingAverageCrossBacktestStrategy(BacktestStrategy):
    name = "Moving Average Cross Strategy"

    def __init__(self, strategy_instance=None, short_period=10, long_period=30):
        super().__init__(strategy_instance)
        self.short_period = short_period
        self.long_period = long_period

        # Detectar si usar sma o ema basado en nombre
        if "ema" in strategy_instance.name.lower():
            self.use_ema = True
        else:
            self.use_ema = False

    def should_generate_signal(self, symbol):
        short_attr = f"{'ema' if self.use_ema else 'sma'}_{self.short_period}"
        long_attr = f"{'ema' if self.use_ema else 'sma'}_{self.long_period}"

        candles = [
            c for c in self.candles
            if c.indicators and getattr(c.indicators, short_attr, None) is not None and getattr(c.indicators, long_attr, None) is not None
        ]

        if len(candles) < self.long_period + 2:
            return None

        curr = candles[-1]
        prev = candles[-2]

        curr_short = getattr(curr.indicators, short_attr)
        curr_long = getattr(curr.indicators, long_attr)
        prev_short = getattr(prev.indicators, short_attr)
        prev_long = getattr(prev.indicators, long_attr)

        signal_type = None
        if prev_short < prev_long and curr_short > curr_long:
            signal_type = SignalType.BUY
        elif prev_short > prev_long and curr_short < curr_long:
            signal_type = SignalType.SELL
        else:
            return None

        slope = curr_long - prev_long
        if abs(slope) < 0.00001:
            return None

        confidence = 50

        # Score: separación relativa + pendiente
        separation = abs(curr_short - curr_long) / curr_long if curr_long != 0 else 0
        confidence += min(separation * 100, 30)

        # Bonus si el slope va a favor
        if signal_type == SignalType.BUY and slope > 0:
            confidence += 10
        elif signal_type == SignalType.SELL and slope < 0:
            confidence += 10

        confidence = min(int(confidence), 100)
        if confidence < 70:
            return None

        return Signal(

            signal=signal_type,
            confidence_score=confidence,
            timestamp=curr.timestamp,
            timeframe=self.timeframe,
            market_data=curr,
            strategy=self.strategy_instance,
            is_from_backtest=True
        )
