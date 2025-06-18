from backtesting.strategies.BacktestStrategy import BacktestStrategy
from backtesting.models.HistoricalSignal import Signal
from core.models.enums import SignalType

class VolumeSpikeBacktestStrategy(BacktestStrategy):
    name = "Volume Spike Breakout Strategy"

    def __init__(self, strategy_instance=None, volume_window=20, volume_multiplier=2.0):
        super().__init__(strategy_instance)
        self.volume_window = volume_window
        self.volume_multiplier = volume_multiplier

    def should_generate_signal(self, symbol):
        candles = [
            c for c in self.candles
            if c.indicators and c.indicators.normalized_volume is not None and c.indicators.rsi_14 is not None
        ]
        if len(candles) < self.volume_window + 6:
            return None

        candles = candles[-(self.volume_window + 6):]  # nos aseguramos del bloque necesario

        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        closes = [c.close for c in candles]
        volumes = [c.indicators.normalized_volume for c in candles]
        rsi_val = candles[-1].indicators.rsi_14

        swing_high = max(highs[-6:-1])
        swing_low = min(lows[-6:-1])

        current_price = closes[-1]
        previous_price = closes[-2]

        broke_high = previous_price <= swing_high and current_price > swing_high
        broke_low = previous_price >= swing_low and current_price < swing_low

        recent_volume = volumes[-1]
        avg_volume = sum(volumes[-self.volume_window:]) / self.volume_window

        if recent_volume < avg_volume * self.volume_multiplier:
            return None

        signal_type = None
        if broke_high and rsi_val < 50:
            signal_type = SignalType.BUY
        elif broke_low and rsi_val > 50:
            signal_type = SignalType.SELL
        else:
            return None

        # Score dinámico
        confidence = 50
        confidence += min((recent_volume - avg_volume) / avg_volume * 50, 30)
        if abs(current_price - (swing_high if signal_type == SignalType.BUY else swing_low)) > 0.01:
            confidence += 10

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
