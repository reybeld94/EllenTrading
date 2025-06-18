from backtesting.strategies.BacktestStrategy import BacktestStrategy
from backtesting.models.HistoricalSignal import Signal
from core.models.enums import SignalType

class CCIBacktestStrategy(BacktestStrategy):
    name = "CCI Extreme Strategy"

    def should_generate_signal(self, symbol):
        candles = [
            c for c in self.candles
            if c.indicators and c.indicators.cci_20 is not None
        ]

        if len(candles) < 2:
            return None

        current = candles[-1].indicators.cci_20
        previous = candles[-2].indicators.cci_20
        slope = current - previous

        if abs(slope) < 5:
            return None  # sin fuerza suficiente

        signal_type = None
        if current < -150 and previous > current:
            signal_type = SignalType.BUY
        elif current > 150 and previous < current:
            signal_type = SignalType.SELL
        else:
            return None

        confidence = 50
        confidence += min(abs(current) / 2, 30)
        if abs(slope) > 20:
            confidence += 10

        confidence = min(int(confidence), 100)
        if confidence < 70:
            return None

        return Signal(

            signal=signal_type,
            confidence_score=int(confidence),
            timestamp=candles[-1].timestamp,
            timeframe=self.timeframe,
            market_data=candles[-1],
            strategy=self.strategy_instance,
            is_from_backtest=True
        )
