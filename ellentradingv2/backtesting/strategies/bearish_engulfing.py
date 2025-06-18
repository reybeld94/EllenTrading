from backtesting.strategies.BacktestStrategy import BacktestStrategy
from backtesting.models.HistoricalSignal import Signal
from core.models.enums import SignalType

class BearishEngulfingBacktestStrategy(BacktestStrategy):
    name = "Bearish Engulfing Pattern"

    def should_generate_signal(self, symbol):
        if len(self.candles) < 2:
            return None

        current = self.candles[-1]
        previous = self.candles[-2]

        # Vela actual bajista, anterior alcista
        if current.close >= current.open or previous.close <= previous.open:
            return None

        # El cuerpo actual envuelve al anterior
        if current.open < previous.close or current.close > previous.open:
            return None

        current_body = abs(current.open - current.close)
        previous_body = abs(previous.close - previous.open)
        body_ratio = current_body / previous_body if previous_body != 0 else 0

        confidence = 50
        if body_ratio > 1.2:
            confidence += 10
        if body_ratio > 1.5:
            confidence += 10

        # Bonus por mayor volumen
        if current.indicators and previous.indicators:
            if current.indicators.normalized_volume and previous.indicators.normalized_volume:
                if current.indicators.normalized_volume > previous.indicators.normalized_volume:
                    confidence += 10

        confidence = min(int(confidence), 100)
        if confidence < 70:
            return None

        return Signal(
            signal=SignalType.SELL,
            confidence_score=confidence,
            timestamp=current.timestamp,
            timeframe=self.timeframe,
            market_data=current,
            strategy=self.strategy_instance,
            is_from_backtest=True
        )

