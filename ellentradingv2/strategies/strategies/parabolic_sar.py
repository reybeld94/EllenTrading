from signals.signal import Signal
from core.models.enums import SignalType
from core.models.symbol import Symbol
from strategies.base.base_entry import EntryStrategy
from django.utils.timezone import now, timedelta
from asgiref.sync import async_to_sync


class ParabolicSARStrategy(EntryStrategy):
    name = "Parabolic SAR Trend Strategy"

    def __init__(self, strategy_instance=None):
        self.name = "Parabolic SAR Trend Strategy"
        super().__init__(strategy_instance)

    def should_generate_signal(self, symbol: Symbol, execution_mode="simulated", candles=None) -> Signal | None:
        bars = candles or self.get_candles(symbol, execution_mode)
        if len(bars) < self.required_bars:
            return None

        # Obtener datos necesarios
        current_bar = bars[-1]
        prev_bar = bars[-2] if len(bars) >= 2 else None

        current_price = current_bar.close
        current_sar = self.get_indicator_value(current_bar, "parabolic_sar")
        prev_sar = self.get_indicator_value(prev_bar, "parabolic_sar") if prev_bar else None
        prev_price = prev_bar.close if prev_bar else current_price

        if current_sar is None:
            return None

        # ✅ SOLO AJUSTAR BASE: Primary base = 40 (era 70)
        confidence = 40
        signal_type = None

        # ✨ NUEVA LÓGICA: Detección de flip más flexible
        # Detectar flip reciente (actual o en proceso)
        bullish_flip = self._detect_bullish_flip(bars, current_price, current_sar, prev_price, prev_sar)
        bearish_flip = self._detect_bearish_flip(bars, current_price, current_sar, prev_price, prev_sar)

        if bullish_flip:
            signal_type = SignalType.BUY
            confidence += bullish_flip  # Bonus por tipo de flip
        elif bearish_flip:
            signal_type = SignalType.SELL
            confidence += bearish_flip  # Bonus por tipo de flip
        else:
            return None

        # ✨ SISTEMA DE BONUS MEJORADO

        # Bonus 1: ADX strength (más flexible)
        try:
            adx_value = self.get_indicator_value(current_bar, "adx")
            if adx_value:
                if adx_value >= 30:
                    confidence += 15  # Trend muy fuerte
                elif adx_value >= 25:
                    confidence += 12  # Trend fuerte
                elif adx_value >= 20:  # ⬇️ Más flexible (era 25)
                    confidence += 8  # Trend moderado
                else:
                    confidence -= 10  # Penalizar mercado lateral
        except:
            pass

        # Bonus 2: Distance from SAR (momentum strength)
        sar_distance = abs(current_price - current_sar) / current_price
        if sar_distance > 0.02:  # 2%+ distance
            confidence += 12
        elif sar_distance > 0.01:  # 1%+ distance
            confidence += 8
        elif sar_distance > 0.005:  # 0.5%+ distance
            confidence += 5

        # Bonus 3: Price momentum confirmation
        if len(bars) >= 3:
            price_momentum = (current_price - bars[-3].close) / bars[-3].close
            momentum_strength = abs(price_momentum)

            if momentum_strength > 0.03:  # 3%+ move in 3 bars
                confidence += 15
            elif momentum_strength > 0.02:  # 2%+ move
                confidence += 10
            elif momentum_strength > 0.01:  # 1%+ move
                confidence += 5

            # Verificar que momentum esté alineado con señal
            if signal_type == SignalType.BUY and price_momentum > 0:
                confidence += 8  # Momentum alcista confirma
            elif signal_type == SignalType.SELL and price_momentum < 0:
                confidence += 8  # Momentum bajista confirma

        # Bonus 4: Volume confirmation
        try:
            current_volume = getattr(current_bar, 'volume', None) or self.get_indicator_value(current_bar, "volume")
            if current_volume and len(bars) >= 10:
                volumes = []
                for bar in bars[-10:]:
                    vol = getattr(bar, 'volume', None) or self.get_indicator_value(bar, "volume")
                    if vol:
                        volumes.append(vol)

                if volumes:
                    avg_volume = sum(volumes) / len(volumes)
                    volume_ratio = current_volume / avg_volume

                    if volume_ratio > 1.8:
                        confidence += 15  # Volume muy alto
                    elif volume_ratio > 1.4:
                        confidence += 10  # Volume alto
                    elif volume_ratio > 1.1:
                        confidence += 5  # Volume moderado
        except:
            pass

        # Bonus 5: Candle confirmation
        candle_body = abs(current_price - current_bar.open)
        candle_range = current_bar.high - current_bar.low
        body_ratio = candle_body / candle_range if candle_range > 0 else 0

        if signal_type == SignalType.BUY and current_price > current_bar.open:
            if body_ratio > 0.7:
                confidence += 12  # Vela verde muy fuerte
            elif body_ratio > 0.5:
                confidence += 8  # Vela verde moderada
        elif signal_type == SignalType.SELL and current_price < current_bar.open:
            if body_ratio > 0.7:
                confidence += 12  # Vela roja muy fuerte
            elif body_ratio > 0.5:
                confidence += 8  # Vela roja moderada

        # Bonus 6: Trend consistency (SMA confirmation)
        try:
            sma_20 = self.get_indicator_value(current_bar, "sma_20")
            sma_50 = self.get_indicator_value(current_bar, "sma_50")

            if sma_20 and sma_50:
                if signal_type == SignalType.BUY:
                    if current_price > sma_20 > sma_50:
                        confidence += 12  # Strong uptrend
                    elif current_price > sma_20:
                        confidence += 6  # Moderate uptrend
                elif signal_type == SignalType.SELL:
                    if current_price < sma_20 < sma_50:
                        confidence += 12  # Strong downtrend
                    elif current_price < sma_20:
                        confidence += 6  # Moderate downtrend
        except:
            pass

        # Bonus 7: SAR acceleration (rapid changes indicate strong momentum)
        if len(bars) >= 5:
            sar_changes = []
            for i in range(-5, -1):
                sar_now = self.get_indicator_value(bars[i], "parabolic_sar")
                sar_prev = self.get_indicator_value(bars[i - 1], "parabolic_sar") if i > -len(bars) else None
                if sar_now and sar_prev:
                    sar_changes.append(abs(sar_now - sar_prev) / sar_prev)

            if sar_changes:
                avg_sar_change = sum(sar_changes) / len(sar_changes)
                if avg_sar_change > 0.02:  # Accelerating SAR
                    confidence += 10

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
            source="parabolic_sar",
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
            source="parabolic_sar",
            strategy=self.strategy_instance,
            timeframe=self.timeframe
        )
        s.timestamp = getattr(current_bar, "timestamp", getattr(current_bar, "start_time", None))
        s.received_at = s.timestamp

        from monitoring.utils import log_event
        async_to_sync(log_event)(
            f"✅ PARABOLIC SAR: {signal_type} for {symbol_obj.symbol} | Price: {current_price:.4f} vs SAR: {current_sar:.4f} | Confidence: {confidence}",
            source='strategies', level='INFO')
        return s

    def _detect_bullish_flip(self, bars, current_price, current_sar, prev_price, prev_sar):
        """Detecta flip alcista con múltiples criterios"""

        # Flip confirmado: SAR ahora está debajo del precio
        if current_sar < current_price:

            # Perfect flip: SAR estaba arriba y ahora está abajo
            if prev_sar and prev_sar >= prev_price:
                return 20  # Flip perfecto

            # Early detection: precio rompió arriba del SAR anterior
            if prev_sar and current_price > prev_sar:
                return 15  # Breakout sobre SAR

            # Sustained bullish: ya estaba en modo alcista pero se fortaleció
            if len(bars) >= 3:
                price_trend = (current_price - bars[-3].close) / bars[-3].close
                if price_trend > 0.01:  # 1%+ momentum
                    return 12  # Trend continuation

            return 8  # Bullish position básica

        return 0

    def _detect_bearish_flip(self, bars, current_price, current_sar, prev_price, prev_sar):
        """Detecta flip bajista con múltiples criterios"""

        # Flip confirmado: SAR ahora está arriba del precio
        if current_sar > current_price:

            # Perfect flip: SAR estaba abajo y ahora está arriba
            if prev_sar and prev_sar <= prev_price:
                return 20  # Flip perfecto

            # Early detection: precio rompió abajo del SAR anterior
            if prev_sar and current_price < prev_sar:
                return 15  # Breakdown bajo SAR

            # Sustained bearish: ya estaba en modo bajista pero se fortaleció
            if len(bars) >= 3:
                price_trend = (current_price - bars[-3].close) / bars[-3].close
                if price_trend < -0.01:  # -1%+ momentum
                    return 12  # Trend continuation

            return 8  # Bearish position básica

        return 0