from signals.signal import Signal
from core.models.enums import SignalType
from core.models.symbol import Symbol
from strategies.base.base_entry import EntryStrategy
from django.utils.timezone import now, timedelta
from asgiref.sync import async_to_sync


class VolumeSpikeStrategy(EntryStrategy):
    name = "Volume Spike Breakout Strategy"

    def __init__(self, strategy_instance=None, volume_window=20, volume_multiplier=1.3, rsi_period=14):
        self.volume_window = volume_window
        self.volume_multiplier = volume_multiplier  # ⬇️ Más realista (era 2.0)
        self.rsi_period = rsi_period
        super().__init__(strategy_instance)

    def should_generate_signal(self, symbol: Symbol, execution_mode="simulated", candles=None) -> Signal | None:
        symbol_obj = Symbol.objects.get(symbol=symbol) if isinstance(symbol, str) else symbol
        bars = candles or self.get_candles(symbol_obj, execution_mode)

        if len(bars) < self.volume_window + 5:
            return None

        # ✨ DETECCIÓN DE VOLUME SPIKE SIMPLIFICADA
        current_bar = bars[-1]
        current_volume = self._get_volume(current_bar)

        if not current_volume:
            return None

        # Calcular volumen promedio
        recent_volumes = []
        for bar in bars[-self.volume_window:]:
            vol = self._get_volume(bar)
            if vol:
                recent_volumes.append(vol)

        if len(recent_volumes) < 10:
            return None

        avg_volume = sum(recent_volumes) / len(recent_volumes)
        volume_ratio = current_volume / avg_volume

        # ✨ FILTRO DE VOLUME SPIKE MÁS FLEXIBLE
        if volume_ratio < self.volume_multiplier:
            return None  # No hay spike significativo

        # ✨ DETECCIÓN DE PRICE ACTION MEJORADA
        current_price = current_bar.close
        current_open = current_bar.open
        prev_close = bars[-2].close if len(bars) >= 2 else current_open

        # Calcular momentum de precio
        price_momentum = (current_price - prev_close) / prev_close
        candle_strength = abs(current_price - current_open) / (current_bar.high - current_bar.low + 1e-8)

        # ✅ SOLO AJUSTAR BASE: Confirm base = 30 (era 65)
        confidence = 30
        signal_type = None

        # ✨ NUEVA LÓGICA: Multiple scenarios para volume spike

        # Scenario 1: Volume spike + strong momentum
        if abs(price_momentum) > 0.015:  # 1.5% move
            if price_momentum > 0:
                signal_type = SignalType.BUY
                confidence += 15  # Momentum alcista fuerte
            else:
                signal_type = SignalType.SELL
                confidence += 15  # Momentum bajista fuerte

        # Scenario 2: Volume spike + breakout of recent range
        elif not signal_type:
            high_range = max(bar.high for bar in bars[-10:-1])  # ⬆️ Más flexible (era [-6:-2])
            low_range = min(bar.low for bar in bars[-10:-1])

            if current_price > high_range:
                signal_type = SignalType.BUY
                confidence += 12  # Breakout alcista
            elif current_price < low_range:
                signal_type = SignalType.SELL
                confidence += 12  # Breakout bajista

        # Scenario 3: Volume spike + strong candle pattern
        elif not signal_type and candle_strength > 0.6:  # Cuerpo dominante
            if current_price > current_open:  # Vela verde
                signal_type = SignalType.BUY
                confidence += 10
            elif current_price < current_open:  # Vela roja
                signal_type = SignalType.SELL
                confidence += 10

        if not signal_type:
            return None

        # ✨ SISTEMA DE BONUS MEJORADO

        # Bonus 1: Intensidad del volume spike
        if volume_ratio > 3.0:
            confidence += 20  # Volume explosion
        elif volume_ratio > 2.0:
            confidence += 15  # Volume muy alto
        elif volume_ratio > 1.5:
            confidence += 10  # Volume alto

        # Bonus 2: Price momentum strength
        momentum_abs = abs(price_momentum)
        if momentum_abs > 0.03:  # 3%+ move
            confidence += 15
        elif momentum_abs > 0.02:  # 2%+ move
            confidence += 10
        elif momentum_abs > 0.01:  # 1%+ move
            confidence += 5

        # Bonus 3: Candle quality
        if candle_strength > 0.8:  # Cuerpo muy dominante
            confidence += 12
        elif candle_strength > 0.6:
            confidence += 8

        # Bonus 4: ⭐ RSI CONFLUENCE (mejorado)
        try:
            rsi_val = self.get_indicator_value(current_bar, f"rsi_{self.rsi_period}")
            if rsi_val:
                # Nueva lógica: RSI confirma momentum, no lo contradice
                if signal_type == SignalType.BUY:
                    if rsi_val < 70:  # No overbought
                        confidence += 8
                        if rsi_val < 50:  # Con espacio para subir
                            confidence += 5
                elif signal_type == SignalType.SELL:
                    if rsi_val > 30:  # No oversold
                        confidence += 8
                        if rsi_val > 50:  # Con espacio para bajar
                            confidence += 5
        except:
            pass

        # Bonus 5: Time of day factor (optional)
        try:
            hour = current_bar.start_time.hour if hasattr(current_bar, 'start_time') else None
            if hour and 9 <= hour <= 11:  # Market open hours (high volume period)
                confidence += 5
        except:
            pass

        # Bonus 6: Trend confirmation
        try:
            sma_20 = self.get_indicator_value(current_bar, "sma_20")
            if sma_20:
                if signal_type == SignalType.BUY and current_price > sma_20:
                    confidence += 8  # Trend alcista
                elif signal_type == SignalType.SELL and current_price < sma_20:
                    confidence += 8  # Trend bajista
        except:
            pass

        # Bonus 7: Gap detection
        gap_size = abs(current_open - prev_close) / prev_close
        if gap_size > 0.005:  # 0.5% gap
            confidence += 8

        # Bonus 8: Volume consistency (not just a single spike)
        if len(recent_volumes) >= 3:
            last_3_avg = sum(recent_volumes[-3:]) / 3
            prev_3_avg = sum(recent_volumes[-6:-3]) / 3 if len(recent_volumes) >= 6 else last_3_avg

            if last_3_avg > prev_3_avg * 1.2:  # Sustained higher volume
                confidence += 10

        confidence = min(int(confidence), 100)

        # ✅ SOLO AJUSTAR THRESHOLD: Confirm threshold = 55 (era 70)
        min_confidence = getattr(self.strategy_instance, "confidence_threshold", 55)
        if confidence < min_confidence:
            return None

        # Evitar duplicados
        timeframe_minutes = int(self.timeframe.replace("m", "")) if "m" in self.timeframe else 60
        recent_cutoff = now() - timedelta(minutes=timeframe_minutes)
        recent_signal = Signal.objects.filter(
            symbol=symbol_obj,
            signal=signal_type,
            source="volume_spike",
            strategy=self.strategy_instance,
            received_at__gte=recent_cutoff
        ).exists()

        if recent_signal:
            return None

        # Crear señal
        s = Signal(
            symbol=symbol_obj,
            signal=signal_type,
            price=current_price,
            confidence_score=confidence,
            source="volume_spike",
            strategy=self.strategy_instance,
            timeframe=self.timeframe
        )
        s.timestamp = getattr(current_bar, "timestamp", getattr(current_bar, "start_time", None))
        s.received_at = s.timestamp

        from monitoring.utils import log_event
        async_to_sync(log_event)(
            f"✅ VOLUME SPIKE: {signal_type} for {symbol_obj.symbol} | Vol Ratio: {volume_ratio:.1f}x | Price Move: {price_momentum:.1%} | Confidence: {confidence}",
            source='strategies', level='INFO')
        return s

    def _get_volume(self, bar):
        """Helper para obtener volumen de diferentes fuentes"""
        volume = getattr(bar, "volume", None)
        if volume is None:
            volume = self.get_indicator_value(bar, "volume")
        return volume