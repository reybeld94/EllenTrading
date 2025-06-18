from backtesting.strategies.BacktestStrategy import BacktestStrategy
from backtesting.models.HistoricalSignal import Signal
from core.models.enums import SignalType

class BullishEngulfingBacktestStrategy(BacktestStrategy):
    name = "Bullish Engulfing Pattern"

    def should_generate_signal(self, symbol):
        if len(self.candles) < 2:
            return None

        current = self.candles[-1]
        previous = self.candles[-2]

        # La vela actual debe ser alcista, la anterior bajista
        if current.close <= current.open or previous.close >= previous.open:
            return None

        # El cuerpo actual debe envolver al anterior
        if current.open > previous.close or current.close < previous.open:
            return None

        # Calcular confianza basada en proporción de cuerpos
        current_body = abs(current.close - current.open)
        previous_body = abs(previous.open - previous.close)
        body_ratio = current_body / previous_body if previous_body != 0 else 0

        confidence = 50
        if body_ratio > 1.2:
            confidence += 10
        if body_ratio > 1.5:
            confidence += 10

        # Bonus por volumen (si tienes normalizado)
        if current.indicators and previous.indicators:
            if current.indicators.normalized_volume and previous.indicators.normalized_volume:
                if current.indicators.normalized_volume > previous.indicators.normalized_volume:
                    confidence += 10

        confidence = min(int(confidence), 100)
        if confidence < 70:
            return None

        return Signal(

            signal=SignalType.BUY,
            confidence_score=confidence,
            timestamp=current.timestamp,
            timeframe=self.timeframe,
            market_data=current,
            strategy=self.strategy_instance,
            is_from_backtest=True
        )
