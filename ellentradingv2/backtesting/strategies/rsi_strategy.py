from backtesting.strategies.BacktestStrategy import BacktestStrategy
from backtesting.models.HistoricalSignal import Signal
from core.models.enums import SignalType

class RSIBreakoutBacktestStrategy(BacktestStrategy):
    name = "RSI Breakout Strategy"

    def should_generate_signal(self, symbol):
        candles = [c for c in self.candles if c.indicators and c.indicators.rsi_14 is not None]
        if len(candles) < 1:
            return None

        rsi_value = candles[-1].indicators.rsi_14
        last_price = candles[-1].close

        signal_type = None
        confidence = 50

        if rsi_value < 30:
            signal_type = SignalType.BUY
            confidence += (30 - rsi_value) * 1.5
        elif rsi_value > 70:
            signal_type = SignalType.SELL
            confidence += (rsi_value - 70) * 1.5
        elif 40 <= rsi_value <= 50:
            signal_type = SignalType.BUY
            confidence += 10
        elif 50 <= rsi_value <= 60:
            signal_type = SignalType.SELL
            confidence += 10
        else:
            return None

        confidence = min(int(confidence), 100)
        if confidence < 70:
            return None

        return Signal(

            signal=signal_type,
            confidence_score=confidence,
            timestamp=candles[-1].timestamp,
            timeframe=self.timeframe,
            market_data=candles[-1],
            strategy=self.strategy_instance,
            is_from_backtest=True
        )
