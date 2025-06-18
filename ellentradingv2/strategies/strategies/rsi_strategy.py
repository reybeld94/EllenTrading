from signals.signal import Signal
from core.models.enums import SignalType
from core.models.symbol import Symbol
from strategies.base.base_entry import EntryStrategy
from django.utils.timezone import now, timedelta
from asgiref.sync import async_to_sync


class RSIBreakoutStrategy(EntryStrategy):
    name = "RSI Breakout Strategy"

    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70
    RSI_REBOUND_MARGIN = 2.0  # Multiplicador más agresivo

    def __init__(self, strategy_instance=None):
        self.name = "RSI Breakout Strategy"
        super().__init__(strategy_instance)

    def should_generate_signal(self, symbol: Symbol, execution_mode="simulated", candles=None) -> Signal | None:
        bars = candles or self.get_candles(symbol, execution_mode)
        if len(bars) < self.required_bars:
            return None

        rsi_curr = self.get_indicator_value(bars[-1], "rsi_14")
        rsi_prev = self.get_indicator_value(bars[-2], "rsi_14") if len(bars) >= 2 else None

        if rsi_curr is None:
            return None

        # ✅ SOLO AJUSTAR BASE: Primary base = 40 (era 60)
        confidence = 40
        signal_type = None

        # Detección de señal principal
        if rsi_curr < self.RSI_OVERSOLD and (rsi_prev is None or rsi_curr > rsi_prev):
            signal_type = SignalType.BUY
            confidence += (self.RSI_OVERSOLD - rsi_curr) * self.RSI_REBOUND_MARGIN

        elif rsi_curr > self.RSI_OVERBOUGHT and (rsi_prev is None or rsi_curr < rsi_prev):
            signal_type = SignalType.SELL
            confidence += (rsi_curr - self.RSI_OVERBOUGHT) * self.RSI_REBOUND_MARGIN
        else:
            return None

        # ✨ BONUS SYSTEM - Nuevos criterios de calidad

        # Bonus 1: RSI extremo (valores muy oversold/overbought)
        if rsi_curr < 25:
            confidence += 15  # RSI muy oversold
        elif rsi_curr > 75:
            confidence += 15  # RSI muy overbought
        elif rsi_curr < 20 or rsi_curr > 80:
            confidence += 25  # RSI extremadamente oversold/overbought

        # Bonus 2: Confirmación de volumen
        try:
            current_volume = getattr(bars[-1], 'volume', None) or self.get_indicator_value(bars[-1], "volume")
            if current_volume and len(bars) >= 10:
                # Calcular volumen promedio de últimas 10 velas
                volumes = []
                for bar in bars[-10:]:
                    vol = getattr(bar, 'volume', None) or self.get_indicator_value(bar, "volume")
                    if vol:
                        volumes.append(vol)

                if volumes:
                    avg_volume = sum(volumes) / len(volumes)
                    volume_ratio = current_volume / avg_volume

                    if volume_ratio > 1.5:
                        confidence += 15  # Volumen muy alto
                    elif volume_ratio > 1.2:
                        confidence += 10  # Volumen alto
        except:
            pass  # Si no hay datos de volumen, continuar sin bonus

        # Bonus 3: Confirmación de vela (price action)
        last_bar = bars[-1]
        body_size = abs(last_bar.close - last_bar.open)
        candle_range = last_bar.high - last_bar.low

        if candle_range > 0:
            body_ratio = body_size / candle_range

            if signal_type == SignalType.BUY:
                if last_bar.close > last_bar.open:  # Vela verde
                    confidence += 8
                    if body_ratio > 0.6:  # Cuerpo dominante
                        confidence += 5
            elif signal_type == SignalType.SELL:
                if last_bar.close < last_bar.open:  # Vela roja
                    confidence += 8
                    if body_ratio > 0.6:  # Cuerpo dominante
                        confidence += 5

        # Bonus 4: Confluencia con trend (SMA confirmation)
        try:
            sma_20 = self.get_indicator_value(bars[-1], "sma_20")
            current_price = bars[-1].close

            if sma_20:
                if signal_type == SignalType.BUY and current_price > sma_20:
                    confidence += 12  # Trend alcista confirma compra
                elif signal_type == SignalType.SELL and current_price < sma_20:
                    confidence += 12  # Trend bajista confirma venta
        except:
            pass

        # Bonus 5: RSI momentum (velocidad de cambio)
        if rsi_prev:
            rsi_momentum = abs(rsi_curr - rsi_prev)
            if rsi_momentum > 5:  # Cambio rápido en RSI
                confidence += 8
            elif rsi_momentum > 8:  # Cambio muy rápido
                confidence += 12

        # Bonus 6: Posición relativa en el rango (qué tan oversold/overbought)
        if signal_type == SignalType.BUY:
            oversold_intensity = (30 - rsi_curr) / 30  # 0 to 1
            confidence += int(oversold_intensity * 10)
        elif signal_type == SignalType.SELL:
            overbought_intensity = (rsi_curr - 70) / 30  # 0 to 1
            confidence += int(overbought_intensity * 10)

        confidence = min(int(confidence), 100)

        # ✅ SOLO AJUSTAR THRESHOLD: Primary threshold = 50 (era 70)
        min_confidence = getattr(self.strategy_instance, "confidence_threshold", 50)
        if confidence < min_confidence:
            return None

        # Evitar duplicados
        symbol_obj = Symbol.objects.get(symbol=symbol) if isinstance(symbol, str) else symbol
        timeframe_minutes = int(self.timeframe.replace("m", "")) if "m" in self.timeframe else 60
        recent_cutoff = now() - timedelta(minutes=timeframe_minutes)
        recent_signal = Signal.objects.filter(
            symbol=symbol_obj,
            signal=signal_type,
            source="rsi_breakout",
            strategy=self.strategy_instance,
            received_at__gte=recent_cutoff
        ).exists()

        if recent_signal:
            return None

        # Crear señal
        s = Signal(
            symbol=symbol_obj,
            signal=signal_type,
            price=bars[-1].close,
            confidence_score=confidence,
            source="rsi_breakout",
            strategy=self.strategy_instance,
            timeframe=self.timeframe
        )
        s.timestamp = getattr(bars[-1], "timestamp", getattr(bars[-1], "start_time", None))
        s.received_at = s.timestamp

        from monitoring.utils import log_event
        async_to_sync(log_event)(
            f"✅ RSI Signal: {signal_type} for {symbol_obj.symbol} | RSI: {rsi_curr:.1f} | Confidence: {confidence}",
            source='strategies', level='INFO')
        return s