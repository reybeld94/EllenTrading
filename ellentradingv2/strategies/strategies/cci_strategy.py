from signals.signal import Signal
from core.models.enums import SignalType
from core.models.symbol import Symbol
from strategies.base.base_entry import EntryStrategy
from django.utils.timezone import now, timedelta
from monitoring.utils import log_event
from asgiref.sync import async_to_sync


class CCIExtremeStrategy(EntryStrategy):
    name = "CCI Extreme Strategy"

    def __init__(self, strategy_instance=None, cci_period=20):
        self.name = "CCI Extreme Strategy"
        self.cci_period = cci_period
        super().__init__(strategy_instance)

    def should_generate_signal(self, symbol: Symbol, execution_mode="simulated", candles=None) -> Signal | None:
        bars = candles or self.get_candles(symbol, execution_mode)
        if len(bars) < self.cci_period + 10:  # Extra bars for analysis
            return None

        current_bar = bars[-1]
        prev_bar = bars[-2] if len(bars) >= 2 else None

        current_cci = self.get_indicator_value(current_bar, f"cci_{self.cci_period}")
        prev_cci = self.get_indicator_value(prev_bar, f"cci_{self.cci_period}") if prev_bar else None

        if current_cci is None:
            return None

        # ✨ CONFIDENCE CON RANGOS UNIVERSALES ESTANDARIZADOS
        # Confirm strategy: base 30 (puede llegar a 55-75 con bonus)
        confidence = 30  # ⬇️ Ajustado de 65 a 30 para seguir rangos universales (Confirm priority)
        signal_type = None

        # ✨ MANTENER TODO EL SISTEMA CCI COMPLETO: Múltiples tipos de señales

        # Signal Type 1: CCI Extreme Reversal (original mejorado)
        extreme_signal, extreme_bonus = self._detect_extreme_reversal(
            current_cci, prev_cci, bars
        )

        # Signal Type 2: CCI Zero Line Cross
        zero_cross_signal, zero_cross_bonus = self._detect_zero_line_cross(
            current_cci, prev_cci, bars
        )

        # Signal Type 3: CCI Divergence with Price
        divergence_signal, divergence_bonus = self._detect_cci_divergence(
            bars, current_cci
        )

        # Signal Type 4: CCI Trend Momentum
        momentum_signal, momentum_bonus = self._detect_cci_momentum(
            current_cci, prev_cci, bars
        )

        # Signal Type 5: CCI Overbought/Oversold with Confirmation
        ob_os_signal, ob_os_bonus = self._detect_overbought_oversold(
            current_cci, prev_cci, current_bar
        )

        # Priorizar señales por fuerza
        if extreme_signal:  # Extreme reversal es la más fuerte
            signal_type = extreme_signal
            confidence += extreme_bonus
        elif divergence_signal:  # Divergence es muy potente
            signal_type = divergence_signal
            confidence += divergence_bonus
        elif zero_cross_signal:  # Zero cross es confiable
            signal_type = zero_cross_signal
            confidence += zero_cross_bonus
        elif momentum_signal:  # Momentum signal
            signal_type = momentum_signal
            confidence += momentum_bonus
        elif ob_os_signal:  # Overbought/oversold
            signal_type = ob_os_signal
            confidence += ob_os_bonus
        else:
            return None

        # ✨ MANTENER TODO EL SISTEMA DE BONUS COMPLETO

        # Bonus 1: CCI extremity level
        extremity_bonus = self._calculate_extremity_bonus(current_cci)
        confidence += extremity_bonus

        # Bonus 2: CCI momentum strength
        momentum_bonus_extra = self._calculate_cci_momentum_bonus(current_cci, prev_cci)
        confidence += momentum_bonus_extra

        # Bonus 3: Price action confirmation
        price_action_bonus = self._calculate_price_action_bonus(current_bar, signal_type)
        confidence += price_action_bonus

        # Bonus 4: Volume confirmation
        volume_bonus = self._calculate_volume_bonus(bars, current_bar)
        confidence += volume_bonus

        # Bonus 5: Trend alignment
        trend_bonus = self._calculate_trend_alignment_bonus(bars, signal_type)
        confidence += trend_bonus

        # Bonus 6: CCI pattern recognition
        pattern_bonus = self._calculate_cci_pattern_bonus(bars, current_cci)
        confidence += pattern_bonus

        # Bonus 7: Multi-timeframe context (simulated)
        context_bonus = self._calculate_context_bonus(bars, current_cci, signal_type)
        confidence += context_bonus

        # ✅ APLICAR RANGOS UNIVERSALES
        confidence = min(int(confidence), 100)

        # ✅ THRESHOLD AJUSTADO A RANGOS UNIVERSALES
        # Para Confirm: 55 (DECENTE alto) mínimo, 70+ (BUENA/FUERTE) preferido
        min_confidence = getattr(self.strategy_instance, "confidence_threshold", 55)
        if confidence < min_confidence:
            return None

        # ✅ OPCIONAL: Log del rango alcanzado
        quality_level = self._get_quality_description(confidence)
        async_to_sync(log_event)(f"📊 CCI Score: {confidence} - {quality_level}",
                                 source='strategies', level='INFO')

        # Evitar duplicados
        symbol_obj = symbol if isinstance(symbol, Symbol) else Symbol.objects.get(symbol=symbol)
        timeframe_minutes = int(self.timeframe.replace("m", "")) if "m" in self.timeframe else 60
        recent_cutoff = now() - timedelta(minutes=timeframe_minutes)
        recent_signal = Signal.objects.filter(
            symbol=symbol_obj,
            signal=signal_type,
            source="cci_extreme",
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
            source="cci_extreme",
            strategy=self.strategy_instance,
            timeframe=self.timeframe
        )
        s.timestamp = getattr(bars[-1], "timestamp", getattr(bars[-1], "start_time", None))
        s.received_at = s.timestamp

        async_to_sync(log_event)(
            f"⚡ CCI EMPOWERED: {signal_type} for {symbol_obj.symbol} | CCI: {current_cci:.1f} | Price: {s.price:.4f} | Confidence: {confidence}",
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

    def _detect_extreme_reversal(self, current_cci, prev_cci, bars):
        """Detecta reversiones desde niveles extremos (mejorado)"""
        if not prev_cci:
            return None, 0

        # ✨ UMBRALES MÁS FLEXIBLES
        extreme_oversold = -120  # Era -150 (más flexible)
        extreme_overbought = 120  # Era 150 (más flexible)

        # Bullish extreme reversal
        if current_cci < extreme_oversold and prev_cci < current_cci:  # CCI subiendo desde extremo
            bonus = 20

            # Extra bonus por qué tan extremo
            if current_cci < -180:
                bonus += 15  # Very extreme
            elif current_cci < -150:
                bonus += 10  # Extreme

            # Bonus por velocidad de recuperación
            recovery_speed = current_cci - prev_cci
            if recovery_speed > 15:
                bonus += 8  # Fast recovery
            elif recovery_speed > 8:
                bonus += 5  # Moderate recovery

            return SignalType.BUY, bonus

        # Bearish extreme reversal
        if current_cci > extreme_overbought and prev_cci > current_cci:  # CCI bajando desde extremo
            bonus = 20

            # Extra bonus por qué tan extremo
            if current_cci > 180:
                bonus += 15  # Very extreme
            elif current_cci > 150:
                bonus += 10  # Extreme

            # Bonus por velocidad de caída
            decline_speed = prev_cci - current_cci
            if decline_speed > 15:
                bonus += 8  # Fast decline
            elif decline_speed > 8:
                bonus += 5  # Moderate decline

            return SignalType.SELL, bonus

        return None, 0

    def _detect_zero_line_cross(self, current_cci, prev_cci, bars):
        """Detecta cruces de línea zero del CCI"""
        if not prev_cci:
            return None, 0

        # Bullish zero cross: CCI cruza arriba de 0
        if prev_cci <= 0 and current_cci > 0:
            bonus = 15

            # Extra bonus si viene de territorio negativo profundo
            if prev_cci < -50:
                bonus += 8

            # Extra bonus por momentum
            momentum = current_cci - prev_cci
            if momentum > 20:
                bonus += 6

            return SignalType.BUY, bonus

        # Bearish zero cross: CCI cruza abajo de 0
        if prev_cci >= 0 and current_cci < 0:
            bonus = 15

            # Extra bonus si viene de territorio positivo alto
            if prev_cci > 50:
                bonus += 8

            # Extra bonus por momentum
            momentum = prev_cci - current_cci
            if momentum > 20:
                bonus += 6

            return SignalType.SELL, bonus

        return None, 0

    def _detect_cci_divergence(self, bars, current_cci):
        """Detecta divergencias entre CCI y precio"""
        if len(bars) < 15:
            return None, 0

        try:
            # Get recent price highs/lows and CCI values
            recent_prices = [bar.close for bar in bars[-15:]]
            recent_cci = []

            for bar in bars[-15:]:
                cci_val = self.get_indicator_value(bar, f"cci_{self.cci_period}")
                if cci_val is not None:
                    recent_cci.append(cci_val)
                else:
                    return None, 0

            if len(recent_cci) < 15:
                return None, 0

            # Bullish divergence: price making lower lows, CCI making higher lows
            price_low_idx = recent_prices.index(min(recent_prices[-10:]))  # Last 10 bars
            cci_low_idx = recent_cci.index(min(recent_cci[-10:]))

            if (price_low_idx != cci_low_idx and
                    recent_prices[-1] < recent_prices[price_low_idx + 5] and  # Price lower low
                    recent_cci[-1] > recent_cci[cci_low_idx + 5]):  # CCI higher low
                return SignalType.BUY, 18

            # Bearish divergence: price making higher highs, CCI making lower highs
            price_high_idx = recent_prices.index(max(recent_prices[-10:]))
            cci_high_idx = recent_cci.index(max(recent_cci[-10:]))

            if (price_high_idx != cci_high_idx and
                    recent_prices[-1] > recent_prices[price_high_idx + 5] and  # Price higher high
                    recent_cci[-1] < recent_cci[cci_high_idx + 5]):  # CCI lower high
                return SignalType.SELL, 18

        except:
            pass

        return None, 0

    def _detect_cci_momentum(self, current_cci, prev_cci, bars):
        """Detecta señales de momentum del CCI"""
        if not prev_cci or len(bars) < 5:
            return None, 0

        # Get CCI trend over last 5 bars
        cci_values = []
        for bar in bars[-5:]:
            val = self.get_indicator_value(bar, f"cci_{self.cci_period}")
            if val is not None:
                cci_values.append(val)

        if len(cci_values) < 5:
            return None, 0

        # Calculate CCI trend
        cci_trend = cci_values[-1] - cci_values[0]  # 5-bar trend
        cci_acceleration = (cci_values[-1] - cci_values[-2]) - (cci_values[-2] - cci_values[-3])

        # Strong bullish momentum
        if cci_trend > 40 and current_cci > -50 and cci_acceleration > 5:
            return SignalType.BUY, 12

        # Strong bearish momentum
        if cci_trend < -40 and current_cci < 50 and cci_acceleration < -5:
            return SignalType.SELL, 12

        return None, 0

    def _detect_overbought_oversold(self, current_cci, prev_cci, current_bar):
        """Detecta señales en niveles overbought/oversold moderados"""
        if not prev_cci:
            return None, 0

        # ✨ NIVELES MODERADOS (no extremos)
        oversold_level = -80  # Era -150
        overbought_level = 80  # Era 150

        # Bullish from oversold with confirmation
        if (oversold_level <= current_cci <= -50 and current_cci > prev_cci and
                current_bar.close > current_bar.open):  # Green candle confirmation
            bonus = 10
            return SignalType.BUY, bonus

        # Bearish from overbought with confirmation
        if (50 <= current_cci <= overbought_level and current_cci < prev_cci and
                current_bar.close < current_bar.open):  # Red candle confirmation
            bonus = 10
            return SignalType.SELL, bonus

        return None, 0

    def _calculate_extremity_bonus(self, current_cci):
        """Calcula bonus basado en qué tan extremo está el CCI"""
        cci_abs = abs(current_cci)

        if cci_abs > 200:
            return 15  # Very extreme
        elif cci_abs > 150:
            return 12  # Extreme
        elif cci_abs > 100:
            return 8  # High
        elif cci_abs > 50:
            return 4  # Moderate
        else:
            return 0  # Neutral

    def _calculate_cci_momentum_bonus(self, current_cci, prev_cci):
        """Calcula bonus basado en momentum del CCI"""
        if not prev_cci:
            return 0

        momentum = abs(current_cci - prev_cci)

        if momentum > 30:
            return 10  # Very fast movement
        elif momentum > 20:
            return 6  # Fast movement
        elif momentum > 10:
            return 3  # Moderate movement
        else:
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

            if volume_ratio > 2.0:
                return 12
            elif volume_ratio > 1.6:
                return 8
            elif volume_ratio > 1.3:
                return 5
            elif volume_ratio > 1.1:
                return 2
            else:
                return 0
        except:
            return 0

    def _calculate_trend_alignment_bonus(self, bars, signal_type):
        """Calcula bonus por alineación con tendencia"""
        if len(bars) < 10:
            return 0

        # Simple trend analysis
        price_trend = (bars[-1].close - bars[-10].close) / bars[-10].close

        if signal_type == SignalType.BUY and price_trend > 0.02:  # 2%+ uptrend
            return 6
        elif signal_type == SignalType.SELL and price_trend < -0.02:  # 2%+ downtrend
            return 6
        else:
            return 0

    def _calculate_cci_pattern_bonus(self, bars, current_cci):
        """Calcula bonus por patrones específicos del CCI"""
        if len(bars) < 8:
            return 0

        # Get recent CCI values
        cci_values = []
        for bar in bars[-8:]:
            val = self.get_indicator_value(bar, f"cci_{self.cci_period}")
            if val is not None:
                cci_values.append(val)

        if len(cci_values) < 6:
            return 0

        # Pattern 1: CCI Hook (reversal pattern)
        if len(cci_values) >= 3:
            if (cci_values[-3] < cci_values[-2] > cci_values[-1] and  # Peak formation
                    abs(cci_values[-2]) > 80):  # At significant level
                return 8

        # Pattern 2: CCI Double bottom/top
        if len(cci_values) >= 6:
            lows = [i for i, val in enumerate(cci_values) if val < -80]
            highs = [i for i, val in enumerate(cci_values) if val > 80]

            if len(lows) >= 2 and current_cci > cci_values[-2]:  # Double bottom + recovery
                return 6
            elif len(highs) >= 2 and current_cci < cci_values[-2]:  # Double top + decline
                return 6

        return 0

    def _calculate_context_bonus(self, bars, current_cci, signal_type):
        """Calcula bonus por contexto multi-timeframe simulado"""
        if len(bars) < 20:
            return 0

        # Longer term CCI trend (simulated higher timeframe)
        longer_cci_values = []
        for i in range(-20, 0, 4):  # Every 4th bar (simulating 4x timeframe)
            try:
                val = self.get_indicator_value(bars[i], f"cci_{self.cci_period}")
                if val is not None:
                    longer_cci_values.append(val)
            except:
                continue

        if len(longer_cci_values) < 3:
            return 0

        longer_trend = longer_cci_values[-1] - longer_cci_values[0]

        # Bonus if signal aligns with longer trend
        if signal_type == SignalType.BUY and longer_trend > 20:
            return 5  # Longer term bullish
        elif signal_type == SignalType.SELL and longer_trend < -20:
            return 5  # Longer term bearish
        else:
            return 0