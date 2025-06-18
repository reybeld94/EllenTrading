from backtesting.strategies.BacktestStrategy import BacktestStrategy
from backtesting.models.HistoricalSignal import Signal
from core.models.enums import SignalType

class ParabolicSARBacktestStrategy(BacktestStrategy):
    name = "Parabolic SAR Trend Strategy"

    def should_generate_signal(self, symbol):
        candles = [
            c for c in self.candles
            if c.indicators and c.indicators.parabolic_sar is not None
        ]
        if len(candles) < 5:
            return None

        # Últimos 5 SARs
        sar_values = [c.indicators.parabolic_sar for c in candles[-5:]]
        closes = [c.close for c in candles[-5:]]

        last_price = closes[-1]
        previous_price = closes[-2]
        previous_sar = sar_values[-2]
        last_3 = sar_values[-3:]

        # Detectar flip válido
        flipped_below = all(dot < close for dot, close in zip(last_3, closes[-3:]))
        flipped_above = all(dot > close for dot, close in zip(last_3, closes[-3:]))

        signal_type = None
        if flipped_below and previous_sar > previous_price:
            signal_type = SignalType.BUY
        elif flipped_above and previous_sar < previous_price:
            signal_type = SignalType.SELL
        else:
            return None

        confidence = 50
        confidence += 10  # flip confirmado
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
