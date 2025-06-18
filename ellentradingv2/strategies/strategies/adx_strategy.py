from signals.signal import Signal
from core.models.enums import SignalType
from core.models.symbol import Symbol
from strategies.base.base_entry import EntryStrategy
from django.utils.timezone import now, timedelta
from monitoring.utils import log_event
from asgiref.sync import async_to_sync


class ADXTrendStrengthStrategy(EntryStrategy):
    name = "ADX Trend Strength Strategy"

    def __init__(self, strategy_instance=None, adx_period=14):
        self.name = "ADX Trend Strength Strategy"
        self.adx_period = adx_period
        super().__init__(strategy_instance)
        self.required_bars = adx_period + 5

    def log(self, message, level="INFO"):
        async_to_sync(log_event)(f"[{self.name}] {message}", source="strategies", level=level)

    def should_generate_signal(self, symbol: Symbol, execution_mode="simulated", candles=None) -> Signal | None:
        bars = candles or self.get_candles(symbol, execution_mode)
        if len(bars) < self.required_bars:
            self.log(f"❌ Faltan velas ({len(bars)}/{self.required_bars}) para {symbol}", level="WARNING")
            return None

        current_bar = bars[-1]
        prev_bar = bars[-2] if len(bars) >= 2 else None

        # Obtener indicadores ADX
        adx_current = self.get_indicator_value(current_bar, "adx")
        plus_di_current = self.get_indicator_value(current_bar, "plus_di")
        minus_di_current = self.get_indicator_value(current_bar, "minus_di")

        adx_prev = self.get_indicator_value(prev_bar, "adx") if prev_bar else None
        plus_di_prev = self.get_indicator_value(prev_bar, "plus_di") if prev_bar else None
        minus_di_prev = self.get_indicator_value(prev_bar, "minus_di") if prev_bar else None

        if None in [adx_current, plus_di_current, minus_di_current]:
            self.log(
                f"❌ Indicadores incompletos: ADX={adx_current}, +DI={plus_di_current}, -DI={minus_di_current} para {symbol}",
                level="WARNING")
            return None

        # ✨ CONFIDENCE CON RANGOS UNIVERSALES ESTANDARIZADOS
        # Primary strategy: base 40 (puede llegar a 65-85 con bonus)
        confidence = 40  # ⬇️ Ajustado de 60 a 40 para seguir rangos universales
        signal_type = None

        # ✨ MANTENER TODA TU LÓGICA COMPLETA DE DETECCIÓN

        # Signal Type 1: Strong ADX with clear DI dominance
        strong_signal, strong_bonus = self._detect_strong_adx_signal(
            adx_current, plus_di_current, minus_di_current, current_bar
        )

        # Signal Type 2: ADX rising (building momentum)
        rising_signal, rising_bonus = self._detect_rising_adx_signal(
            adx_current, adx_prev, plus_di_current, minus_di_current,
            plus_di_prev, minus_di_prev, current_bar
        )

        # Signal Type 3: DI crossover with ADX confirmation
        crossover_signal, crossover_bonus = self._detect_di_crossover(
            plus_di_current, minus_di_current, plus_di_prev, minus_di_prev,
            adx_current, current_bar
        )

        # Signal Type 4: ADX breakout from low levels
        breakout_signal, breakout_bonus = self._detect_adx_breakout(
            adx_current, adx_prev, bars, plus_di_current, minus_di_current, current_bar
        )

        # Priorizar señales por fuerza
        if strong_signal:
            signal_type = strong_signal
            confidence += strong_bonus
        elif rising_signal:
            signal_type = rising_signal
            confidence += rising_bonus
        elif crossover_signal:
            signal_type = crossover_signal
            confidence += crossover_bonus
        elif breakout_signal:
            signal_type = breakout_signal
            confidence += breakout_bonus
        else:
            self.log(f"❌ Ninguna señal ADX válida para {symbol}")
            return None

        # ✨ MANTENER TODO TU SISTEMA DE BONUS COMPLETO

        # Bonus 1: ADX strength levels (más granular)
        adx_bonus = self._calculate_adx_strength_bonus(adx_current)
        confidence += adx_bonus

        # Bonus 2: DI separation (decisiveness)
        di_separation_bonus = self._calculate_di_separation_bonus(plus_di_current, minus_di_current)
        confidence += di_separation_bonus

        # Bonus 3: ADX momentum (rising vs falling)
        momentum_bonus = self._calculate_adx_momentum_bonus(adx_current, adx_prev, signal_type)
        confidence += momentum_bonus

        # Bonus 4: Price action confirmation
        price_action_bonus = self._calculate_price_action_bonus(current_bar, signal_type)
        confidence += price_action_bonus

        # Bonus 5: Volume confirmation
        volume_bonus = self._calculate_volume_bonus(bars, current_bar)
        confidence += volume_bonus

        # Bonus 6: Trend consistency (multi-timeframe simulation)
        trend_bonus = self._calculate_trend_consistency_bonus(bars, signal_type)
        confidence += trend_bonus

        # Bonus 7: ADX pattern recognition
        pattern_bonus = self._calculate_adx_pattern_bonus(bars, adx_current)
        confidence += pattern_bonus

        # ✅ APLICAR RANGOS UNIVERSALES
        confidence = min(int(confidence), 100)

        # ✅ THRESHOLD AJUSTADO A RANGOS UNIVERSALES
        # Para Primary: 50 (DECENTE) mínimo, 65+ (BUENA) preferido
        min_confidence = getattr(self.strategy_instance, "confidence_threshold", 50)
        if confidence < min_confidence:
            self.log(f"❌ Confianza {confidence} < mínimo requerido ({min_confidence}) para {symbol}", level="WARNING")
            return None

        # ✅ OPCIONAL: Log del rango alcanzado
        quality_level = self._get_quality_description(confidence)
        self.log(f"📊 ADX Score: {confidence} - {quality_level}")

        # Evitar señales duplicadas
        symbol_obj = Symbol.objects.get(symbol=symbol) if isinstance(symbol, str) else symbol
        timeframe_minutes = int(self.timeframe.replace("m", "")) if "m" in self.timeframe else 0
        recent_cutoff = now() - timedelta(minutes=timeframe_minutes)
        recent_signal = Signal.objects.filter(
            symbol=symbol_obj,
            signal=signal_type,
            source="adx_trend",
            strategy=self.strategy_instance,
            received_at__gte=recent_cutoff
        ).exists()

        if recent_signal:
            self.log(f"🚫 Ya existe una señal {signal_type} reciente para {symbol}")
            return None

        # Crear señal
        s = Signal(
            symbol=symbol_obj,
            signal=signal_type,
            price=current_bar.close,
            confidence_score=confidence,
            source="adx_trend",
            strategy=self.strategy_instance,
            timeframe=self.timeframe
        )
        s.timestamp = getattr(current_bar, "timestamp", getattr(current_bar, "start_time", None))
        s.received_at = s.timestamp

        self.log(
            f"✅ ADX Signal: {signal_type} para {symbol_obj.symbol} @ {s.price} | ADX: {adx_current:.1f} | +DI: {plus_di_current:.1f} | -DI: {minus_di_current:.1f} | Confidence: {confidence}")
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

    def _detect_strong_adx_signal(self, adx, plus_di, minus_di, current_bar):
        """Detecta señales con ADX fuerte y clara dominancia DI"""
        if adx < 30:
            return None, 0

        di_difference = abs(plus_di - minus_di)
        if di_difference < 5:
            return None, 0

        # Confirmación de vela
        candle_confirms = self._candle_confirms_direction(current_bar, plus_di > minus_di)
        if not candle_confirms:
            return None, 0

        if plus_di > minus_di:
            bonus = 20  # Strong bullish
            if adx > 40:
                bonus += 8
            return SignalType.BUY, bonus
        else:
            bonus = 20  # Strong bearish
            if adx > 40:
                bonus += 8
            return SignalType.SELL, bonus

    def _detect_rising_adx_signal(self, adx, adx_prev, plus_di, minus_di, plus_di_prev, minus_di_prev, current_bar):
        """Detecta señales con ADX en aumento (building momentum)"""
        if not adx_prev or adx < 20:
            return None, 0

        adx_rise = adx - adx_prev
        if adx_rise < 2:
            return None, 0

        # DI debe mostrar dirección clara
        if abs(plus_di - minus_di) < 3:
            return None, 0

        # Confirmación de vela
        candle_confirms = self._candle_confirms_direction(current_bar, plus_di > minus_di)
        if not candle_confirms:
            return None, 0

        if plus_di > minus_di:
            bonus = 15
            if adx_rise > 5:
                bonus += 5
            return SignalType.BUY, bonus
        else:
            bonus = 15
            if adx_rise > 5:
                bonus += 5
            return SignalType.SELL, bonus

    def _detect_di_crossover(self, plus_di, minus_di, plus_di_prev, minus_di_prev, adx, current_bar):
        """Detecta crossovers de DI con confirmación ADX"""
        if not all([plus_di_prev, minus_di_prev]) or adx < 20:
            return None, 0

        # Bullish DI crossover: +DI crosses above -DI
        if plus_di_prev <= minus_di_prev and plus_di > minus_di:
            if self._candle_confirms_direction(current_bar, True):
                bonus = 12
                if adx > 25:
                    bonus += 5
                return SignalType.BUY, bonus

        # Bearish DI crossover: +DI crosses below -DI
        if plus_di_prev >= minus_di_prev and plus_di < minus_di:
            if self._candle_confirms_direction(current_bar, False):
                bonus = 12
                if adx > 25:
                    bonus += 5
                return SignalType.SELL, bonus

        return None, 0

    def _detect_adx_breakout(self, adx, adx_prev, bars, plus_di, minus_di, current_bar):
        """Detecta breakout de ADX desde niveles bajos"""
        if not adx_prev or len(bars) < 10:
            return None, 0

        # ADX estaba bajo y ahora está rompiendo
        if adx_prev < 20 and adx >= 25:
            # Verificar que estuvo en niveles bajos por un tiempo
            recent_adx_values = []
            for bar in bars[-10:-1]:
                val = self.get_indicator_value(bar, "adx")
                if val:
                    recent_adx_values.append(val)

            if recent_adx_values and max(recent_adx_values) < 25:
                # Clear DI direction
                if abs(plus_di - minus_di) > 5:
                    if plus_di > minus_di and self._candle_confirms_direction(current_bar, True):
                        return SignalType.BUY, 18
                    elif minus_di > plus_di and self._candle_confirms_direction(current_bar, False):
                        return SignalType.SELL, 18

        return None, 0

    def _candle_confirms_direction(self, bar, is_bullish):
        """Verifica que la vela confirme la dirección esperada"""
        if is_bullish:
            return bar.close > bar.open
        else:
            return bar.close < bar.open

    def _calculate_adx_strength_bonus(self, adx):
        """Calcula bonus basado en la fuerza del ADX"""
        if adx >= 50:
            return 15
        elif adx >= 40:
            return 12
        elif adx >= 30:
            return 8
        elif adx >= 25:
            return 5
        else:
            return 0

    def _calculate_di_separation_bonus(self, plus_di, minus_di):
        """Calcula bonus basado en la separación entre +DI y -DI"""
        separation = abs(plus_di - minus_di)

        if separation > 20:
            return 12
        elif separation > 15:
            return 8
        elif separation > 10:
            return 5
        elif separation > 5:
            return 2
        else:
            return 0

    def _calculate_adx_momentum_bonus(self, adx, adx_prev, signal_type):
        """Calcula bonus basado en el momentum del ADX"""
        if not adx_prev:
            return 0

        adx_momentum = adx - adx_prev

        if adx_momentum > 5:
            return 10
        elif adx_momentum > 2:
            return 6
        elif adx_momentum > 0:
            return 3
        elif adx_momentum < -5:
            return -5
        else:
            return 0

    def _calculate_price_action_bonus(self, current_bar, signal_type):
        """Calcula bonus basado en price action"""
        candle_body = abs(current_bar.close - current_bar.open)
        candle_range = current_bar.high - current_bar.low
        body_ratio = candle_body / candle_range if candle_range > 0 else 0

        bonus = 0

        # Strong candle in signal direction
        if signal_type == SignalType.BUY and current_bar.close > current_bar.open:
            if body_ratio > 0.7:
                bonus = 8
            elif body_ratio > 0.5:
                bonus = 5
        elif signal_type == SignalType.SELL and current_bar.close < current_bar.open:
            if body_ratio > 0.7:
                bonus = 8
            elif body_ratio > 0.5:
                bonus = 5

        return bonus

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

    def _calculate_trend_consistency_bonus(self, bars, signal_type):
        """Calcula bonus por consistencia de tendencia"""
        if len(bars) < 5:
            return 0

        # Simple trend analysis
        prices = [bar.close for bar in bars[-5:]]

        if signal_type == SignalType.BUY:
            # Check for ascending prices
            ascending = all(prices[i] <= prices[i + 1] for i in range(len(prices) - 1))
            if ascending:
                return 8
            elif prices[-1] > prices[0]:
                return 4
        elif signal_type == SignalType.SELL:
            # Check for descending prices
            descending = all(prices[i] >= prices[i + 1] for i in range(len(prices) - 1))
            if descending:
                return 8
            elif prices[-1] < prices[0]:
                return 4

        return 0

    def _calculate_adx_pattern_bonus(self, bars, current_adx):
        """Calcula bonus por patrones de ADX"""
        if len(bars) < 5:
            return 0

        # Get recent ADX values
        adx_values = []
        for bar in bars[-5:]:
            val = self.get_indicator_value(bar, "adx")
            if val:
                adx_values.append(val)

        if len(adx_values) < 4:
            return 0

        # Check for ADX accelerating pattern
        if len(adx_values) >= 3:
            slope1 = adx_values[-2] - adx_values[-3]
            slope2 = adx_values[-1] - adx_values[-2]

            # Accelerating upward ADX
            if slope1 > 0 and slope2 > slope1:
                return 6

        return 0