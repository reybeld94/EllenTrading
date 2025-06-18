from backtesting.strategies.BacktestStrategy import BacktestStrategy
from backtesting.models.HistoricalSignal import Signal
from core.models.enums import SignalType

class ADXBacktestStrategy(BacktestStrategy):
    name = "ADX Trend Strength Strategy"

    def should_generate_signal(self, symbol):
        candles = [
            c for c in self.candles
            if c.indicators and all([
                c.indicators.adx is not None,
                c.indicators.plus_di is not None,
                c.indicators.minus_di is not None
            ])
        ]
        if len(candles) < 1:
            return None

        last = candles[-1]
        i = last.indicators

        adx_value = i.adx
        plus_di = i.plus_di
        minus_di = i.minus_di

        if adx_value < 20:
            return None  # sin tendencia clara

        signal_type = None
        confidence = 50

        if plus_di > minus_di and last.close > last.open:
            signal_type = SignalType.BUY
        elif minus_di > plus_di and last.close < last.open:
            signal_type = SignalType.SELL
        else:
            return None

        # Escalar confianza según fuerza del ADX
        if 25 <= adx_value < 35:
            confidence += 10
        elif 35 <= adx_value < 50:
            confidence += 20
        elif adx_value >= 50:
            confidence += 30

        # Bonus por cuerpo dominante de vela
        if abs(last.close - last.open) > ((last.high - last.low) * 0.6):
            confidence += 10

        confidence = min(int(confidence), 100)
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
