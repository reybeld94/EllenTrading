from backtesting.strategies.BacktestStrategy import BacktestStrategy
from backtesting.models.HistoricalSignal import Signal
from core.models.enums import SignalType

class MACDBacktestStrategy(BacktestStrategy):
    name = "MACD Crossover Strategy"

    def should_generate_signal(self, symbol):
        candles = [c for c in self.candles if c.indicators and c.indicators.macd is not None and c.indicators.macd_signal is not None and c.indicators.macd_hist is not None]
        if len(candles) < 2:
            return None

        prev = candles[-2].indicators
        curr = candles[-1].indicators

        prev_macd = prev.macd
        curr_macd = curr.macd
        prev_signal = prev.macd_signal
        curr_signal = curr.macd_signal
        prev_hist = prev.macd_hist
        curr_hist = curr.macd_hist

        signal_type = None
        confidence = 50

        if prev_macd < prev_signal and curr_macd > curr_signal:
            signal_type = SignalType.BUY
            confidence += min(abs(curr_macd - curr_signal) * 50, 20)
            if abs(curr_macd) < 0.2:
                confidence += 10
            if curr_hist > prev_hist:
                confidence += 5  
        elif prev_macd > prev_signal and curr_macd < curr_signal:
            signal_type = SignalType.SELL
            confidence += min(abs(curr_signal - curr_macd) * 50, 20)
            if abs(curr_macd) < 0.2:
                confidence += 10
            if curr_hist < prev_hist:
                confidence += 5
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
