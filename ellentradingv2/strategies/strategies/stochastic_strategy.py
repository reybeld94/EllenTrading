from signals.signal import Signal
from core.models.enums import SignalType
from core.models.symbol import Symbol
from strategies.base.base_entry import EntryStrategy
from django.utils.timezone import now, timedelta
from asgiref.sync import async_to_sync


class StochasticOscillatorStrategy(EntryStrategy):
    name = "Stochastic Oscillator Strategy"

    # ✨ THRESHOLDS MÁS DINÁMICOS
    EXTREME_OVERBOUGHT = 85  # Era 80 (más estricto)
    EXTREME_OVERSOLD = 15  # Era 20 (más estricto)
    MODERATE_OVERBOUGHT = 75  # Nuevo nivel
    MODERATE_OVERSOLD = 25  # Nuevo nivel
    SIGNAL_DIFF_THRESHOLD = 3  # Era 5 (más sensible)
    DEFAULT_CONFIDENCE_THRESHOLD = 70
    INDICATOR_K = "stochastic_k"
    INDICATOR_D = "stochastic_d"
    SOURCE = "stochastic_oscillator"

    def __init__(self, strategy_instance=None):
        self.name = "Stochastic Oscillator Strategy"
        super().__init__(strategy_instance)

    def should_generate_signal(self, symbol: Symbol, execution_mode="simulated", candles=None) -> Signal | None:
        bars = candles or self.get_candles(symbol, execution_mode)
        if len(bars) < self.required_bars:
            return None

        current_bar = bars[-1]
        prev_bar = bars[-2] if len(bars) >= 2 else None

        k_current = self.get_indicator_value(current_bar, self.INDICATOR_K)
        d_current = self.get_indicator_value(current_bar, self.INDICATOR_D)
        k_prev = self.get_indicator_value(prev_bar, self.INDICATOR_K) if prev_bar else None
        d_prev = self.get_indicator_value(prev_bar, self.INDICATOR_D) if prev_bar else None

        if None in [k_current, d_current]:
            return None

        # ✅ SOLO AJUSTAR BASE: Confirm base = 30 (era 65)
        confidence = 30
        signal_type = None

        # ✨ SISTEMA STOCHASTIC COMPLETO: Múltiples tipos de señales

        # Signal Type 1: Classic Stochastic Cross in extreme zones
        cross_signal, cross_bonus = self._detect_stochastic_cross(
            k_current, d_current, k_prev, d_prev
        )

        # Signal Type 2: Stochastic Divergence with Price
        divergence_signal, divergence_bonus = self._detect_stochastic_divergence(
            bars, k_current, d_current
        )

        # Signal Type 3: Extreme bounce (reversal from very oversold/overbought)
        extreme_signal, extreme_bonus = self._detect_extreme_bounce(
            k_current, d_current, k_prev, d_prev, bars
        )

        # Signal Type 4: Stochastic momentum (rapid movement)
        momentum_signal, momentum_bonus = self._detect_stochastic_momentum(
            k_current, d_current, k_prev, d_prev, bars
        )

        # Signal Type 5: Double bottom/top in stochastic
        pattern_signal, pattern_bonus = self._detect_stochastic_patterns(
            bars, k_current, d_current
        )

        # Priorizar señales por fuerza
        if divergence_signal:  # Divergence es la más potente
            signal_type = divergence_signal
            confidence += divergence_bonus
        elif extreme_signal:  # Extreme bounce es muy fuerte
            signal_type = extreme_signal
            confidence += extreme_bonus
        elif cross_signal:  # Classic cross
            signal_type = cross_signal
            confidence += cross_bonus
        elif pattern_signal:  # Pattern recognition
            signal_type = pattern_signal
            confidence += pattern_bonus
        elif momentum_signal:  # Momentum
            signal_type = momentum_signal
            confidence += momentum_bonus
        else:
            return None

        # ✨ SISTEMA DE BONUS MEJORADO

        # Bonus 1: Stochastic position strength
        position_bonus = self._calculate_position_bonus(k_current, d_current, signal_type)
        confidence += position_bonus

        # Bonus 2: Stochastic momentum strength
        momentum_bonus_extra = self._calculate_momentum_bonus(k_current, d_current, k_prev, d_prev)
        confidence += momentum_bonus_extra

        # Bonus 3: Volume confirmation
        volume_bonus = self._calculate_volume_bonus(bars, current_bar)
        confidence += volume_bonus

        # Bonus 4: Price action confirmation
        price_action_bonus = self._calculate_price_action_bonus(current_bar, signal_type)
        confidence += price_action_bonus

        # Bonus 5: Trend alignment
        trend_bonus = self._calculate_trend_alignment_bonus(bars, signal_type)
        confidence += trend_bonus

        # Bonus 6: Multiple timeframe context (simulated)
        mtf_bonus = self._calculate_multi_timeframe_bonus(bars, signal_type)
        confidence += mtf_bonus

        # Bonus 7: Stochastic cycle analysis
        cycle_bonus = self._calculate_cycle_bonus(bars, k_current, d_current)
        confidence += cycle_bonus

        # Bonus 8: Support/Resistance confluence
        sr_bonus = self._calculate_support_resistance_bonus(bars, current_bar.close)
        confidence += sr_bonus

        confidence = min(int(confidence), 100)

        # ✅ SOLO AJUSTAR THRESHOLD: Confirm threshold = 55 (era 70)
        min_confidence = getattr(self.strategy_instance, "confidence_threshold", 55)
        if confidence < min_confidence:
            return None

        # Evitar duplicados
        symbol_obj = symbol if isinstance(symbol, Symbol) else Symbol.objects.get(symbol=symbol)
        timeframe_minutes = int(self.timeframe.replace("m", "")) if "m" in self.timeframe else 0
        recent_cutoff = now() - timedelta(minutes=timeframe_minutes)
        recent_signal = Signal.objects.filter(
            symbol=symbol_obj,
            signal=signal_type,
            source=self.SOURCE,
            strategy=self.strategy_instance,
            received_at__gte=recent_cutoff
        ).exists()

        if recent_signal:
            return None

        # Crear señal
        s = Signal(
            symbol=symbol_obj,
            signal=signal_type,
            price=current_bar.close,
            confidence_score=confidence,
            source=self.SOURCE,
            strategy=self.strategy_instance,
            timeframe=self.timeframe
        )
        s.timestamp = getattr(current_bar, "timestamp", getattr(current_bar, "start_time", None))
        s.received_at = s.timestamp

        from monitoring.utils import log_event
        async_to_sync(log_event)(
            f"📈 STOCHASTIC MASTER: {signal_type} for {symbol_obj.symbol} | %K: {k_current:.1f} | %D: {d_current:.1f} | Confidence: {confidence}",
            source='strategies', level='INFO')
        return s

    def _detect_stochastic_cross(self, k_current, d_current, k_prev, d_prev):
        """Detecta cruces de %K y %D en zonas extremas"""
        if not all([k_prev, d_prev]):
            return None, 0

        # ✨ CRUCES MÁS INTELIGENTES

        # Bullish cross in oversold territory
        if (k_prev <= d_prev and k_current > d_current and
                d_current < self.MODERATE_OVERSOLD):  # Era solo en extreme oversold

            bonus = 15  # Base bonus for cross

            # Extra bonus por qué tan oversold
            if d_current < self.EXTREME_OVERSOLD:
                bonus += 12  # Very oversold cross
            elif d_current < self.MODERATE_OVERSOLD:
                bonus += 8  # Moderately oversold cross

            # Bonus por fuerza del cruce
            cross_strength = k_current - d_current
            if cross_strength > 8:
                bonus += 6  # Strong cross
            elif cross_strength > 4:
                bonus += 3  # Moderate cross

            return SignalType.BUY, bonus

        # Bearish cross in overbought territory
        if (k_prev >= d_prev and k_current < d_current and
                d_current > self.MODERATE_OVERBOUGHT):  # Era solo en extreme overbought

            bonus = 15  # Base bonus for cross

            # Extra bonus por qué tan overbought
            if d_current > self.EXTREME_OVERBOUGHT:
                bonus += 12  # Very overbought cross
            elif d_current > self.MODERATE_OVERBOUGHT:
                bonus += 8  # Moderately overbought cross

            # Bonus por fuerza del cruce
            cross_strength = d_current - k_current
            if cross_strength > 8:
                bonus += 6  # Strong cross
            elif cross_strength > 4:
                bonus += 3  # Moderate cross

            return SignalType.SELL, bonus

        return None, 0

    def _detect_stochastic_divergence(self, bars, k_current, d_current):
        """Detecta divergencias entre Stochastic y precio"""
        if len(bars) < 15:
            return None, 0

        try:
            # Get recent price and stochastic data
            recent_prices = [bar.close for bar in bars[-15:]]
            recent_k_values = []

            for bar in bars[-15:]:
                k_val = self.get_indicator_value(bar, self.INDICATOR_K)
                if k_val is not None:
                    recent_k_values.append(k_val)
                else:
                    return None, 0

            if len(recent_k_values) < 15:
                return None, 0

            # Bullish divergence: price making lower lows, stochastic making higher lows
            price_recent_low = min(recent_prices[-10:])
            stoch_recent_low = min(recent_k_values[-10:])

            price_prev_low = min(recent_prices[-15:-5])
            stoch_prev_low = min(recent_k_values[-15:-5])

            if (price_recent_low < price_prev_low and  # Price lower low
                    stoch_recent_low > stoch_prev_low and  # Stochastic higher low
                    k_current < 40):  # Still in lower territory
                return SignalType.BUY, 20  # Strong divergence signal

            # Bearish divergence: price making higher highs, stochastic making lower highs
            price_recent_high = max(recent_prices[-10:])
            stoch_recent_high = max(recent_k_values[-10:])

            price_prev_high = max(recent_prices[-15:-5])
            stoch_prev_high = max(recent_k_values[-15:-5])

            if (price_recent_high > price_prev_high and  # Price higher high
                    stoch_recent_high < stoch_prev_high and  # Stochastic lower high
                    k_current > 60):  # Still in upper territory
                return SignalType.SELL, 20  # Strong divergence signal

        except:
            pass

        return None, 0

    def _detect_extreme_bounce(self, k_current, d_current, k_prev, d_prev, bars):
        """Detecta rebotes desde niveles extremos"""
        if not all([k_prev, d_prev]):
            return None, 0

        # ✨ REBOTES DESDE EXTREMOS MÁS POTENTES

        # Bullish bounce from extreme oversold
        if (d_prev < self.EXTREME_OVERSOLD and d_current > d_prev and
                k_current > k_prev and k_current > d_current):

            bonus = 18  # Strong bounce signal

            # Extra bonus por qué tan extremo estaba
            if d_prev < 10:
                bonus += 12  # Extremely oversold bounce
            elif d_prev < self.EXTREME_OVERSOLD:
                bonus += 8  # Very oversold bounce

            # Bonus por velocidad de recuperación
            recovery_speed = k_current - k_prev
            if recovery_speed > 15:
                bonus += 8  # Very fast recovery
            elif recovery_speed > 8:
                bonus += 5  # Fast recovery

            return SignalType.BUY, bonus

        # Bearish bounce from extreme overbought
        if (d_prev > self.EXTREME_OVERBOUGHT and d_current < d_prev and
                k_current < k_prev and k_current < d_current):

            bonus = 18  # Strong bounce signal

            # Extra bonus por qué tan extremo estaba
            if d_prev > 90:
                bonus += 12  # Extremely overbought bounce
            elif d_prev > self.EXTREME_OVERBOUGHT:
                bonus += 8  # Very overbought bounce

            # Bonus por velocidad de caída
            decline_speed = k_prev - k_current
            if decline_speed > 15:
                bonus += 8  # Very fast decline
            elif decline_speed > 8:
                bonus += 5  # Fast decline

            return SignalType.SELL, bonus

        return None, 0

    def _detect_stochastic_momentum(self, k_current, d_current, k_prev, d_prev, bars):
        """Detecta momentum rápido en stochastic"""
        if not all([k_prev, d_prev]) or len(bars) < 5:
            return None, 0

        # Get stochastic values for momentum analysis
        k_values = []
        for bar in bars[-5:]:
            k_val = self.get_indicator_value(bar, self.INDICATOR_K)
            if k_val is not None:
                k_values.append(k_val)

        if len(k_values) < 5:
            return None, 0

        # Calculate momentum over last 5 periods
        momentum = k_values[-1] - k_values[0]  # 5-period momentum
        acceleration = (k_values[-1] - k_values[-2]) - (k_values[-2] - k_values[-3])

        # Strong bullish momentum from lower levels
        if (momentum > 25 and k_current > d_current and
                k_current < 70 and acceleration > 3):
            return SignalType.BUY, 14

        # Strong bearish momentum from upper levels
        if (momentum < -25 and k_current < d_current and
                k_current > 30 and acceleration < -3):
            return SignalType.SELL, 14

        return None, 0

    def _detect_stochastic_patterns(self, bars, k_current, d_current):
        """Detecta patrones específicos en stochastic"""
        if len(bars) < 10:
            return None, 0

        # Get recent stochastic values
        k_values = []
        d_values = []

        for bar in bars[-10:]:
            k_val = self.get_indicator_value(bar, self.INDICATOR_K)
            d_val = self.get_indicator_value(bar, self.INDICATOR_D)
            if k_val is not None and d_val is not None:
                k_values.append(k_val)
                d_values.append(d_val)

        if len(k_values) < 8:
            return None, 0

        # Double bottom pattern in stochastic
        if len(k_values) >= 8:
            # Find two lows in oversold territory
            lows = [(i, val) for i, val in enumerate(k_values) if val < 35]
            if len(lows) >= 2:
                last_low = lows[-1]
                prev_low = lows[-2]

                # Double bottom: similar low levels with recovery between
                if (abs(last_low[1] - prev_low[1]) < 10 and  # Similar levels
                        last_low[0] - prev_low[0] >= 3 and  # At least 3 periods apart
                        k_current > last_low[1] + 5):  # Currently recovering
                    return SignalType.BUY, 16

        # Double top pattern in stochastic
        if len(k_values) >= 8:
            # Find two highs in overbought territory
            highs = [(i, val) for i, val in enumerate(k_values) if val > 65]
            if len(highs) >= 2:
                last_high = highs[-1]
                prev_high = highs[-2]

                # Double top: similar high levels with decline between
                if (abs(last_high[1] - prev_high[1]) < 10 and  # Similar levels
                        last_high[0] - prev_high[0] >= 3 and  # At least 3 periods apart
                        k_current < last_high[1] - 5):  # Currently declining
                    return SignalType.SELL, 16

        return None, 0

    def _calculate_position_bonus(self, k_current, d_current, signal_type):
        """Calcula bonus basado en posición en el rango stochastic"""
        bonus = 0

        # Bonus for extreme positions
        if signal_type == SignalType.BUY:
            if d_current < 15:
                bonus += 10  # Very oversold
            elif d_current < 25:
                bonus += 6  # Oversold
        elif signal_type == SignalType.SELL:
            if d_current > 85:
                bonus += 10  # Very overbought
            elif d_current > 75:
                bonus += 6  # Overbought

        # Bonus for %K and %D alignment
        k_d_diff = abs(k_current - d_current)
        if k_d_diff > 10:
            bonus += 4  # Strong divergence between %K and %D

        return bonus

    def _calculate_momentum_bonus(self, k_current, d_current, k_prev, d_prev):
        """Calcula bonus basado en momentum del stochastic"""
        if not all([k_prev, d_prev]):
            return 0

        k_momentum = k_current - k_prev
        d_momentum = d_current - d_prev

        momentum_strength = abs(k_momentum)

        if momentum_strength > 12:
            return 8  # Very fast movement
        elif momentum_strength > 6:
            return 5  # Fast movement
        elif momentum_strength > 3:
            return 2  # Moderate movement
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

            if volume_ratio > 1.8:
                return 10
            elif volume_ratio > 1.4:
                return 6
            elif volume_ratio > 1.1:
                return 3
            else:
                return 0
        except:
            return 0

    def _calculate_price_action_bonus(self, current_bar, signal_type):
        """Calcula bonus basado en price action"""
        candle_body = abs(current_bar.close - current_bar.open)
        candle_range = current_bar.high - current_bar.low
        body_ratio = candle_body / candle_range if candle_range > 0 else 0

        if signal_type == SignalType.BUY and current_bar.close > current_bar.open and body_ratio > 0.6:
            return 8  # Strong green candle
        elif signal_type == SignalType.SELL and current_bar.close < current_bar.open and body_ratio > 0.6:
            return 8  # Strong red candle
        elif body_ratio > 0.4:
            return 4  # Moderate candle
        else:
            return 0

    def _calculate_trend_alignment_bonus(self, bars, signal_type):
        """Calcula bonus por alineación con tendencia"""
        if len(bars) < 20:
            return 0

        # Simple trend analysis
        short_trend = (bars[-1].close - bars[-5].close) / bars[-5].close
        medium_trend = (bars[-1].close - bars[-20].close) / bars[-20].close

        if signal_type == SignalType.BUY and medium_trend > 0.02:
            return 8  # Bullish trend alignment
        elif signal_type == SignalType.SELL and medium_trend < -0.02:
            return 8  # Bearish trend alignment
        else:
            return 0

    def _calculate_multi_timeframe_bonus(self, bars, signal_type):
        """Calcula bonus por contexto multi-timeframe simulado"""
        if len(bars) < 20:
            return 0

        # Simulate higher timeframe by sampling every 4th bar
        htf_bars = bars[::4]

        if len(htf_bars) < 5:
            return 0

        # HTF trend
        htf_trend = (htf_bars[-1].close - htf_bars[0].close) / htf_bars[0].close

        if signal_type == SignalType.BUY and htf_trend > 0.05:
            return 6  # HTF bullish
        elif signal_type == SignalType.SELL and htf_trend < -0.05:
            return 6  # HTF bearish
        else:
            return 0

    def _calculate_cycle_bonus(self, bars, k_current, d_current):
        """Calcula bonus por análisis de ciclo stochastic"""
        if len(bars) < 15:
            return 0

        # Count oscillations in recent period
        k_values = []
        for bar in bars[-15:]:
            k_val = self.get_indicator_value(bar, self.INDICATOR_K)
            if k_val is not None:
                k_values.append(k_val)

        if len(k_values) < 10:
            return 0

        # Count peaks and troughs
        peaks = 0
        troughs = 0

        for i in range(1, len(k_values) - 1):
            if k_values[i] > k_values[i - 1] and k_values[i] > k_values[i + 1] and k_values[i] > 70:
                peaks += 1
            elif k_values[i] < k_values[i - 1] and k_values[i] < k_values[i + 1] and k_values[i] < 30:
                troughs += 1

        # Bonus for proper oscillation (good for stochastic signals)
        if peaks >= 1 and troughs >= 1:
            return 5  # Good oscillation pattern
        else:
            return 0

    def _calculate_support_resistance_bonus(self, bars, current_price):
        """Calcula bonus por confluencia con soporte/resistencia"""
        if len(bars) < 20:
            return 0

        # Simple S/R analysis
        recent_highs = [bar.high for bar in bars[-20:]]
        recent_lows = [bar.low for bar in bars[-20:]]

        resistance_level = max(recent_highs)
        support_level = min(recent_lows)

        # Bonus if near key levels
        resistance_distance = abs(current_price - resistance_level) / current_price
        support_distance = abs(current_price - support_level) / current_price

        if resistance_distance < 0.02:  # Within 2% of resistance
            return 6
        elif support_distance < 0.02:  # Within 2% of support
            return 6
        else:
            return 0