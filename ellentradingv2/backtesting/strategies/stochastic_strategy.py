from backtesting.strategies.BacktestStrategy import BacktestStrategy
from backtesting.models.HistoricalSignal import Signal
from core.models.enums import SignalType

class StochasticBacktestStrategy(BacktestStrategy):
    name = "Stochastic Oscillator Strategy"

    def should_generate_signal(self, symbol):
        candles = [
            c for c in self.candles
            if c.indicators and c.indicators.stochastic_k is not None and c.indicators.stochastic_d is not None
        ]

        if len(candles) < 1:
            return None

        k = candles[-1].indicators.stochastic_k
        d = candles[-1].indicators.stochastic_d

        confidence = 50
        signal_type = None

        # Lógica original respetada 1:1
        if k > d and d < 20:  # BUY desde sobreventa
            signal_type = SignalType.BUY
            confidence += min((20 - d) * 1.5, 30)
            if k - d > 5:
                confidence += 10
        elif k < d and d > 80:  # SELL desde sobrecompra
            signal_type = SignalType.SELL
            confidence += min((d - 80) * 1.5, 30)
            if d - k > 5:
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
