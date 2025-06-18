from signals.signal import Signal
from core.models.enums import SignalType
from core.models.symbol import Symbol
from strategies.base.base_entry import EntryStrategy
from django.utils.timezone import now, timedelta
from monitoring.utils import log_event
from asgiref.sync import async_to_sync


class DonchianChannelBreakoutStrategy(EntryStrategy):
    name = "Donchian Channel Breakout"

    def __init__(self, strategy_instance=None, period=20):
        self.name = "Donchian Channel Breakout"
        self.period = period
        super().__init__(strategy_instance)

    def should_generate_signal(self, symbol: Symbol, execution_mode="simulated", candles=None) -> Signal | None:
        bars = candles or self.get_candles(symbol, execution_mode)
        if len(bars) < self.period + 5:
            return None

        current_bar = bars[-1]
        prev_bar = bars[-2] if len(bars) >= 2 else None
        current_price = current_bar.close
        prev_price = prev_bar.close if prev_bar else current_price

        # Obtener Donchian Channel
        upper = self.get_indicator_value(current_bar, "donchian_upper")
        lower = self.get_indicator_value(current_bar, "donchian_lower")

        # Fallback: calcular manualmente si no hay indicadores
        if upper is None or lower is None:
            highs = [bar.high for bar in bars[-self.period:]]
            lows = [bar.low for bar in bars[-self.period:]]
            upper = max(highs)
            lower = min(lows)

        middle = (upper + lower) / 2

        # ✨ CONFIDENCE CON RANGOS UNIVERSALES ESTANDARIZADOS
        # Primary strategy: base 40 (puede llegar a 65-85 con bonus)
        confidence = 40  # ⬇️ Ajustado de 70 a 40 para seguir rangos universales (Primary priority)
        signal_type = None

        # ✨ MANTENER TODA LA LÓGICA COMPLETA: Detección de BREAKOUTS REALES

        # Signal Type 1: TRUE BREAKOUT (precio ROMPE el canal)
        breakout_signal, breakout_bonus = self._detect_true_breakout(
            current_price, prev_price, upper, lower, bars
        )

        # Signal Type 2: RETEST después de breakout
        retest_signal, retest_bonus = self._detect_retest_signal(
            current_price, upper, lower, bars
        )

        # Signal Type 3: SQUEEZE EXPANSION (canal estrecho que se expande)
        squeeze_signal, squeeze_bonus = self._detect_squeeze_expansion(
            upper, lower, current_price, bars
        )

        # Signal Type 4: MOMENTUM BREAKOUT (breakout + fuerte momentum)
        momentum_signal, momentum_bonus = self._detect_momentum_breakout(
            current_price, prev_price, upper, lower, current_bar
        )

        # Priorizar señales por fuerza
        if breakout_signal:
            signal_type = breakout_signal
            confidence += breakout_bonus
        elif momentum_signal:
            signal_type = momentum_signal
            confidence += momentum_bonus
        elif squeeze_signal:
            signal_type = squeeze_signal
            confidence += squeeze_bonus
        elif retest_signal:
            signal_type = retest_signal
            confidence += retest_bonus
        else:
            return None

        # ✨ MANTENER TODO EL SISTEMA DE BONUS COMPLETO

        # Bonus 1: Channel width (volatility context)
        width_bonus = self._calculate_channel_width_bonus(upper, lower, middle)
        confidence += width_bonus

        # Bonus 2: Distance from breakout point
        distance_bonus = self._calculate_breakout_distance_bonus(current_price, upper, lower, signal_type)
        confidence += distance_bonus

        # Bonus 3: Volume confirmation
        volume_bonus = self._calculate_volume_bonus(bars, current_bar)
        confidence += volume_bonus

        # Bonus 4: Price momentum strength
        momentum_bonus_extra = self._calculate_momentum_bonus(bars, signal_type, current_price)
        confidence += momentum_bonus_extra

        # Bonus 5: Trend alignment (OPCIONAL, no restrictivo)
        trend_bonus = self._calculate_trend_bonus(current_bar, signal_type)
        confidence += trend_bonus

        # Bonus 6: Time since last breakout
        timing_bonus = self._calculate_timing_bonus(bars, upper, lower)
        confidence += timing_bonus

        # Bonus 7: Candle strength
        candle_bonus = self._calculate_candle_bonus(current_bar, signal_type)
        confidence += candle_bonus

        # Bonus 8: Channel position history
        position_bonus = self._calculate_position_history_bonus(bars, upper, lower, current_price)
        confidence += position_bonus

        # ✅ APLICAR RANGOS UNIVERSALES
        confidence = min(int(confidence), 100)

        # ✅ THRESHOLD AJUSTADO A RANGOS UNIVERSALES
        # Para Primary: 50 (DECENTE) mínimo, 65+ (BUENA) preferido
        min_confidence = getattr(self.strategy_instance, "confidence_threshold", 50)
        if confidence < min_confidence:
            return None

        # ✅ OPCIONAL: Log del rango alcanzado
        quality_level = self._get_quality_description(confidence)
        async_to_sync(log_event)(f"📊 Donchian Score: {confidence} - {quality_level}",
                                 source='strategies', level='INFO')

        # Evitar duplicados
        symbol_obj = Symbol.objects.get(symbol=symbol) if isinstance(symbol, str) else symbol
        timeframe_minutes = int(self.timeframe.replace("m", "")) if "m" in self.timeframe else 60
        recent_cutoff = now() - timedelta(minutes=timeframe_minutes)
        recent_signal = Signal.objects.filter(
            symbol=symbol_obj,
            signal=signal_type,
            source="donchian_breakout",
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
            source="donchian_breakout",
            strategy=self.strategy_instance,
            timeframe=self.timeframe
        )
        s.timestamp = getattr(current_bar, "timestamp", getattr(current_bar, "start_time", None))
        s.received_at = s.timestamp

        async_to_sync(log_event)(
            f"🚀 DONCHIAN AWAKENS! {signal_type} for {symbol_obj.symbol} | Price: {current_price:.4f} | Upper: {upper:.4f} | Lower: {lower:.4f} | Confidence: {confidence}",
            source='strategies', level='INFO')
        return s

    def _get_quality_description(self, score: int) -> str:
        """Determina el nivel de calidad según rangos universales"""
        if score <= 34:
            return "🔴 RUIDO"
        elif score <= 49:
            return "🟡 DÉBIL"
        elif score <= 64:
            return "🟠 DECENTE"
        elif score <= 74:
            return "🟢 BUENA"
        elif score <= 84:
            return "🔵 FUERTE"
        else:
            return "🟣 EXCELENTE"

    def _detect_true_breakout(self, current_price, prev_price, upper, lower, bars):
        """Detecta VERDADEROS breakouts del canal (no solo estar arriba/abajo)"""

        # Bullish breakout: precio ROMPE por arriba del canal
        if prev_price <= upper and current_price > upper:
            bonus = 25  # Strong breakout signal

            # Extra bonus si el breakout es decisivo
            breakout_strength = (current_price - upper) / upper
            if breakout_strength > 0.02:  # 2%+ breakout
                bonus += 10
            elif breakout_strength > 0.01:  # 1%+ breakout
                bonus += 5

            return SignalType.BUY, bonus

        # Bearish breakout: precio ROMPE por abajo del canal
        if prev_price >= lower and current_price < lower:
            bonus = 25  # Strong breakout signal

            # Extra bonus si el breakout es decisivo
            breakout_strength = (lower - current_price) / lower
            if breakout_strength > 0.02:  # 2%+ breakout
                bonus += 10
            elif breakout_strength > 0.01:  # 1%+ breakout
                bonus += 5

            return SignalType.SELL, bonus

        return None, 0

    def _detect_retest_signal(self, current_price, upper, lower, bars):
        """Detecta retest exitoso después de breakout"""
        if len(bars) < 5:
            return None, 0

        # Look for recent breakout followed by retest
        recent_prices = [bar.close for bar in bars[-5:]]

        # Bullish retest: precio vuelve a upper como soporte
        if any(p > upper for p in recent_prices[:-1]) and abs(current_price - upper) / upper < 0.01:
            if current_price > upper * 0.998:  # Just above upper
                return SignalType.BUY, 15

        # Bearish retest: precio vuelve a lower como resistencia
        if any(p < lower for p in recent_prices[:-1]) and abs(current_price - lower) / lower < 0.01:
            if current_price < lower * 1.002:  # Just below lower
                return SignalType.SELL, 15

        return None, 0

    def _detect_squeeze_expansion(self, upper, lower, current_price, bars):
        """Detecta expansión después de squeeze (canal estrecho)"""
        if len(bars) < 10:
            return None, 0

        # Calculate current channel width
        current_width = (upper - lower) / lower

        # Get historical widths
        historical_widths = []
        for i in range(-10, -1):
            try:
                bar = bars[i]
                hist_upper = self.get_indicator_value(bar, "donchian_upper")
                hist_lower = self.get_indicator_value(bar, "donchian_lower")
                if hist_upper and hist_lower:
                    width = (hist_upper - hist_lower) / hist_lower
                    historical_widths.append(width)
            except:
                continue

        if not historical_widths:
            return None, 0

        avg_width = sum(historical_widths) / len(historical_widths)

        # Check if expanding from squeeze
        if current_width > avg_width * 1.3:  # 30% wider than average
            if current_price > upper:
                return SignalType.BUY, 18  # Expansion breakout up
            elif current_price < lower:
                return SignalType.SELL, 18  # Expansion breakout down

        return None, 0

    def _detect_momentum_breakout(self, current_price, prev_price, upper, lower, current_bar):
        """Detecta breakout con fuerte momentum"""

        # Price momentum
        price_momentum = (current_price - prev_price) / prev_price

        # Candle strength
        candle_body = abs(current_bar.close - current_bar.open)
        candle_range = current_bar.high - current_bar.low
        body_ratio = candle_body / candle_range if candle_range > 0 else 0

        # Bullish momentum breakout
        if (current_price > upper and price_momentum > 0.015 and  # 1.5%+ momentum
                body_ratio > 0.6 and current_bar.close > current_bar.open):
            return SignalType.BUY, 20

        # Bearish momentum breakout
        if (current_price < lower and price_momentum < -0.015 and  # -1.5%+ momentum
                body_ratio > 0.6 and current_bar.close < current_bar.open):
            return SignalType.SELL, 20

        return None, 0

    def _calculate_channel_width_bonus(self, upper, lower, middle):
        """Calcula bonus basado en ancho del canal"""
        width_ratio = (upper - lower) / middle

        if width_ratio > 0.15:  # Very wide channel (high volatility)
            return 12
        elif width_ratio > 0.08:  # Wide channel
            return 8
        elif width_ratio > 0.04:  # Normal channel
            return 5
        else:
            return 2  # Narrow channel

    def _calculate_breakout_distance_bonus(self, current_price, upper, lower, signal_type):
        """Calcula bonus basado en qué tan lejos está del breakout point"""
        if signal_type == SignalType.BUY:
            distance = (current_price - upper) / upper
        else:
            distance = (lower - current_price) / lower

        if distance > 0.03:  # 3%+ beyond breakout
            return 15
        elif distance > 0.02:  # 2%+ beyond breakout
            return 10
        elif distance > 0.01:  # 1%+ beyond breakout
            return 6
        elif distance > 0.005:  # 0.5%+ beyond breakout
            return 3
        else:
            return 0

    def _calculate_volume_bonus(self, bars, current_bar):
        """Calcula bonus basado en volumen"""
        try:
            current_volume = getattr(current_bar, 'volume', None) or self.get_indicator_value(current_bar, "volume")
            if not current_volume or len(bars) < 10:
                return 0

            volumes = []
            for bar in bars[-10:]:
                vol = getattr(bar, 'volume', None) or self.get_indicator_value(bar, "volume")
                if vol:
                    volumes.append(vol)

            if not volumes:
                return 0

            avg_volume = sum(volumes) / len(volumes)
            volume_ratio = current_volume / avg_volume

            if volume_ratio > 2.5:
                return 15  # Huge volume
            elif volume_ratio > 2.0:
                return 12  # Very high volume
            elif volume_ratio > 1.5:
                return 8  # High volume
            elif volume_ratio > 1.2:
                return 4  # Moderate volume
            else:
                return 0
        except:
            return 0

    def _calculate_momentum_bonus(self, bars, signal_type, current_price):
        """Calcula bonus basado en momentum del precio"""
        if len(bars) < 5:
            return 0

        price_momentum = (current_price - bars[-5].close) / bars[-5].close
        momentum_strength = abs(price_momentum)

        bonus = 0
        if momentum_strength > 0.05:  # 5%+ momentum
            bonus = 12
        elif momentum_strength > 0.03:  # 3%+ momentum
            bonus = 8
        elif momentum_strength > 0.02:  # 2%+ momentum
            bonus = 5

        # Verify momentum aligns with signal
        if signal_type == SignalType.BUY and price_momentum > 0:
            return bonus
        elif signal_type == SignalType.SELL and price_momentum < 0:
            return bonus
        else:
            return bonus // 2  # Partial credit for opposing momentum

    def _calculate_trend_bonus(self, current_bar, signal_type):
        """Calcula bonus por alineación con tendencia (OPCIONAL, no restrictivo)"""
        try:
            sma_20 = self.get_indicator_value(current_bar, "sma_20")
            current_price = current_bar.close

            if sma_20:
                if signal_type == SignalType.BUY and current_price > sma_20:
                    return 6  # Trend aligned (bonus, not requirement)
                elif signal_type == SignalType.SELL and current_price < sma_20:
                    return 6  # Trend aligned
            return 0  # No penalty for misalignment
        except:
            return 0

    def _calculate_timing_bonus(self, bars, upper, lower):
        """Calcula bonus basado en cuánto tiempo ha estado en el canal"""
        if len(bars) < 10:
            return 0

        # Count bars where price was within channel recently
        bars_in_channel = 0
        for bar in bars[-10:-1]:  # Last 9 bars
            if lower <= bar.close <= upper:
                bars_in_channel += 1

        # More time in channel = bigger breakout potential
        if bars_in_channel >= 7:
            return 10  # Long consolidation
        elif bars_in_channel >= 5:
            return 6  # Medium consolidation
        elif bars_in_channel >= 3:
            return 3  # Short consolidation
        else:
            return 0

    def _calculate_candle_bonus(self, current_bar, signal_type):
        """Calcula bonus basado en fuerza de la vela"""
        candle_body = abs(current_bar.close - current_bar.open)
        candle_range = current_bar.high - current_bar.low
        body_ratio = candle_body / candle_range if candle_range > 0 else 0

        if signal_type == SignalType.BUY and current_bar.close > current_bar.open and body_ratio > 0.7:
            return 8  # Very strong green candle
        elif signal_type == SignalType.SELL and current_bar.close < current_bar.open and body_ratio > 0.7:
            return 8  # Very strong red candle
        elif body_ratio > 0.5:
            return 4  # Moderate candle
        else:
            return 0

    def _calculate_position_history_bonus(self, bars, upper, lower, current_price):
        """Calcula bonus basado en historial de posición en el canal"""
        if len(bars) < 5:
            return 0

        # Analyze where price has been in the channel recently
        recent_positions = []
        for bar in bars[-5:-1]:  # Last 4 bars
            if upper != lower:
                position = (bar.close - lower) / (upper - lower)  # 0 to 1
                recent_positions.append(position)

        if not recent_positions:
            return 0

        avg_position = sum(recent_positions) / len(recent_positions)

        # Bonus for breaking out from opposite extreme
        if current_price > upper and avg_position < 0.3:  # Was near bottom, broke top
            return 8
        elif current_price < lower and avg_position > 0.7:  # Was near top, broke bottom
            return 8
        else:
            return 0