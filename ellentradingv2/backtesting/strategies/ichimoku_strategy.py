from backtesting.strategies.BacktestStrategy import BacktestStrategy
from backtesting.models.HistoricalSignal import Signal
from core.models.enums import SignalType

class IchimokuBacktestStrategy(BacktestStrategy):
    name = "Ichimoku Cloud Breakout"

    def should_generate_signal(self, symbol):
        candles = [c for c in self.candles if c.indicators and all([
            c.indicators.ichimoku_tenkan is not None,
            c.indicators.ichimoku_kijun is not None,
            c.indicators.ichimoku_span_a is not None,
            c.indicators.ichimoku_span_b is not None,
            c.indicators.ichimoku_chikou is not None
        ])]
        if len(candles) < 1:
            return None

        last = candles[-1]
        i = last.indicators

        current_price = last.close
        tenkan = i.ichimoku_tenkan
        kijun = i.ichimoku_kijun
        span_a = i.ichimoku_span_a
        span_b = i.ichimoku_span_b
        chikou = i.ichimoku_chikou

        # Evitar nube plana o indefinida
        if any(x is None for x in [tenkan, kijun, span_a, span_b, chikou]):
            return None

        signal_type = None

        bullish = (
            current_price > max(span_a, span_b) and
            tenkan > kijun and
            chikou > current_price
        )

        bearish = (
            current_price < min(span_a, span_b) and
            tenkan < kijun and
            chikou < current_price
        )

        if bullish:
            signal_type = SignalType.BUY
        elif bearish:
            signal_type = SignalType.SELL
        else:
            return None

        # Calcular score
        confidence = 50
        cloud_thickness = abs(span_a - span_b)
        confidence += min(cloud_thickness * 100, 20)
        confidence += 10 if abs(tenkan - kijun) > (current_price * 0.001) else 0
        confidence += 10 if signal_type == SignalType.BUY and chikou > current_price else 0
        confidence += 10 if signal_type == SignalType.SELL and chikou < current_price else 0
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
