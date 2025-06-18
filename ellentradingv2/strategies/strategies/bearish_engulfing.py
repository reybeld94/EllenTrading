from signals.signal import Signal
from core.models.enums import SignalType
from core.models.symbol import Symbol
from strategies.base.base_entry import EntryStrategy
from django.utils.timezone import now, timedelta
from monitoring.utils import log_event
from asgiref.sync import async_to_sync


class BearishEngulfingStrategy(EntryStrategy):
    name = "Bearish Engulfing Pattern"

    def __init__(self, strategy_instance=None):
        self.name = "Bearish Engulfing Pattern"
        super().__init__(strategy_instance)
        self.required_bars = 20  # More bars for context analysis
        self.timeframe = getattr(strategy_instance, "timeframe", "1h")

    def should_generate_signal(self, symbol: Symbol, execution_mode="simulated", candles=None) -> Signal | None:
        bars = candles or self.get_candles(symbol, execution_mode)

        if len(bars) < self.required_bars:
            return None

        current_bar = bars[-1]
        prev_bar = bars[-2]
        current_price = current_bar.close

        # ✨ CONFIDENCE CON RANGOS UNIVERSALES ESTANDARIZADOS
        # Confirm strategy: base 30 (puede llegar a 55-75 con bonus)
        confidence = 30  # ⬇️ Ajustado de 70 a 30 para seguir rangos universales (Confirm priority)
        signal_type = None

        # ✨ MANTENER TODA LA LÓGICA COMPLETA DE DETECCIÓN DE PATRONES

        # Pattern Type 1: Classic Bearish Engulfing
        classic_pattern, classic_bonus = self._detect_classic_bearish_engulfing(prev_bar, current_bar)

        # Pattern Type 2: Dark Cloud Cover (variation)
        dark_cloud_pattern, dark_cloud_bonus = self._detect_dark_cloud_cover(prev_bar, current_bar)

        # Pattern Type 3: Shooting Star/Gravestone reversal patterns
        reversal_pattern, reversal_bonus = self._detect_reversal_patterns(bars, current_bar)

        # Pattern Type 4: Three Black Crows
        crows_pattern, crows_bonus = self._detect_three_black_crows(bars)

        # Priorizar patrones por fuerza
        if classic_pattern:
            signal_type = SignalType.SELL
            confidence += classic_bonus
        elif dark_cloud_pattern:
            signal_type = SignalType.SELL
            confidence += dark_cloud_bonus
        elif crows_pattern:
            signal_type = SignalType.SELL
            confidence += crows_bonus
        elif reversal_pattern:
            signal_type = SignalType.SELL
            confidence += reversal_bonus
        else:
            return None

        # ✨ MANTENER TODO EL SISTEMA DE BONUS CONTEXTUAL COMPLETO

        # Bonus 1: Resistance context
        resistance_bonus = self._calculate_resistance_bonus(bars, current_price)
        confidence += resistance_bonus

        # Bonus 2: Trend context (reversal vs continuation)
        trend_bonus = self._calculate_trend_context_bonus(bars, signal_type)
        confidence += trend_bonus

        # Bonus 3: Volume confirmation
        volume_bonus = self._calculate_volume_bonus(bars, current_bar)
        confidence += volume_bonus

        # Bonus 4: Pattern quality
        quality_bonus = self._calculate_pattern_quality_bonus(prev_bar, current_bar)
        confidence += quality_bonus

        # Bonus 5: Technical indicator confluence
        indicator_bonus = self._calculate_indicator_confluence_bonus(current_bar, signal_type)
        confidence += indicator_bonus

        # Bonus 6: Pattern completion timing
        timing_bonus = self._calculate_timing_bonus(bars)
        confidence += timing_bonus

        # Bonus 7: Market structure context
        structure_bonus = self._calculate_market_structure_bonus(bars, current_price)
        confidence += structure_bonus

        # ✅ APLICAR RANGOS UNIVERSALES
        confidence = min(int(confidence), 100)

        # ✅ THRESHOLD AJUSTADO A RANGOS UNIVERSALES
        # Para Confirm: 55 (DECENTE alto) mínimo, 70+ (BUENA/FUERTE) preferido
        min_confidence = getattr(self.strategy_instance, "confidence_threshold", 55)
        if confidence < min_confidence:
            return None

        # ✅ OPCIONAL: Log del rango alcanzado
        quality_level = self._get_quality_description(confidence)
        async_to_sync(log_event)(f"📊 Bearish Engulfing Score: {confidence} - {quality_level}",
                                 source='strategies', level='INFO')

        # Evitar duplicados
        symbol_obj = self._get_symbol_object(symbol)
        timeframe_minutes = int(self.timeframe.replace("m", "")) if "m" in self.timeframe else 60
        recent_cutoff = now() - timedelta(minutes=timeframe_minutes)
        recent_signal = Signal.objects.filter(
            symbol=symbol_obj,
            signal=SignalType.SELL,
            source="bearish_engulfing",
            strategy=self.strategy_instance,
            received_at__gte=recent_cutoff
        ).exists()

        if recent_signal:
            return None

        # Crear señal
        s = Signal(
            symbol=symbol_obj,
            signal=SignalType.SELL,
            price=current_price,
            confidence_score=int(confidence),
            source="bearish_engulfing",
            strategy=self.strategy_instance,
            timeframe=self.timeframe
        )
        s.timestamp = getattr(current_bar, "timestamp", getattr(current_bar, "start_time", None))
        s.received_at = s.timestamp

        async_to_sync(log_event)(
            f"🕯️ BEARISH ENGULFING: {signal_type} for {symbol_obj.symbol} | Price: {current_price:.4f} | Confidence: {confidence}",
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

    def _detect_classic_bearish_engulfing(self, prev_bar, current_bar):
        """Detecta patrón bearish engulfing clásico"""
        # Previous candle is bullish (green)
        if not (prev_bar.close > prev_bar.open):
            return False, 0

        # Current candle is bearish (red)
        if not (current_bar.open > current_bar.close):
            return False, 0

        # Current candle engulfs previous candle
        if not (current_bar.open >= prev_bar.close and current_bar.close <= prev_bar.open):
            return False, 0

        # Calculate engulfing strength
        prev_body = abs(prev_bar.close - prev_bar.open)
        current_body = abs(current_bar.open - current_bar.close)
        body_ratio = current_body / prev_body if prev_body > 0 else 1

        bonus = 20  # Base bonus for classic pattern

        # Extra bonus for strong engulfing
        if body_ratio > 2.0:
            bonus += 15  # Very strong engulfing
        elif body_ratio > 1.5:
            bonus += 10  # Strong engulfing
        elif body_ratio > 1.2:
            bonus += 5  # Moderate engulfing

        return True, bonus

    def _detect_dark_cloud_cover(self, prev_bar, current_bar):
        """Detecta patrón dark cloud cover"""
        # Previous candle is bullish
        if not (prev_bar.close > prev_bar.open):
            return False, 0

        # Current candle is bearish
        if not (current_bar.open > current_bar.close):
            return False, 0

        # Current candle opens above previous high and closes below midpoint
        prev_midpoint = (prev_bar.open + prev_bar.close) / 2
        if not (current_bar.open > prev_bar.high and current_bar.close < prev_midpoint):
            return False, 0

        # Calculate cloud cover strength
        prev_body = abs(prev_bar.close - prev_bar.open)
        penetration_depth = (prev_bar.close - current_bar.close) / prev_body

        bonus = 15  # Base bonus for dark cloud

        if penetration_depth > 0.7:
            bonus += 10  # Deep penetration
        elif penetration_depth > 0.5:
            bonus += 6  # Moderate penetration

        return True, bonus

    def _detect_reversal_patterns(self, bars, current_bar):
        """Detecta otros patrones de reversión bajista"""
        if len(bars) < 3:
            return False, 0

        # Shooting star pattern
        body = abs(current_bar.close - current_bar.open)
        lower_shadow = min(current_bar.open, current_bar.close) - current_bar.low
        upper_shadow = current_bar.high - max(current_bar.open, current_bar.close)
        total_range = current_bar.high - current_bar.low

        if total_range == 0:
            return False, 0

        # Shooting star: long upper shadow, small body, small lower shadow
        if (upper_shadow > body * 2 and
                lower_shadow < body * 0.5 and
                body / total_range < 0.3):
            return True, 12  # Shooting star pattern

        # Gravestone doji: upper shadow, no body, no lower shadow
        if (body / total_range < 0.1 and
                upper_shadow > total_range * 0.7 and
                lower_shadow < total_range * 0.1):
            return True, 15  # Gravestone doji

        return False, 0

    def _detect_three_black_crows(self, bars):
        """Detecta patrón three black crows"""
        if len(bars) < 3:
            return False, 0

        last_three = bars[-3:]

        # All three candles must be bearish
        all_bearish = all(bar.open > bar.close for bar in last_three)
        if not all_bearish:
            return False, 0

        # Each candle should close lower than the previous
        descending_closes = all(last_three[i].close > last_three[i + 1].close for i in range(2))
        if not descending_closes:
            return False, 0

        # Bodies should be substantial
        min_body_ratio = min(abs(bar.open - bar.close) / (bar.high - bar.low)
                             for bar in last_three if bar.high != bar.low)

        if min_body_ratio > 0.6:
            return True, 18  # Strong three black crows
        elif min_body_ratio > 0.4:
            return True, 12  # Moderate three black crows

        return False, 0

    def _calculate_resistance_bonus(self, bars, current_price):
        """Calcula bonus por contexto de resistencia"""
        if len(bars) < 20:
            return 0

        recent_highs = [bar.high for bar in bars[-20:]]
        resistance_levels = sorted(set(recent_highs), reverse=True)[:5]

        for resistance in resistance_levels:
            distance = abs(current_price - resistance) / current_price
            if distance < 0.02:  # Within 2% of resistance
                return 15  # Strong resistance rejection context

        return 0

    def _calculate_trend_context_bonus(self, bars, signal_type):
        """Calcula bonus por contexto de tendencia (invertido)"""
        if len(bars) < 20:
            return 0

        short_trend = (bars[-1].close - bars[-5].close) / bars[-5].close
        medium_trend = (bars[-1].close - bars[-20].close) / bars[-20].close

        # Bearish reversal in uptrend is strongest
        if signal_type == SignalType.SELL:
            if medium_trend > 0.05 and short_trend > 0.02:
                return 12  # Strong reversal setup
            elif medium_trend > 0.02:
                return 8  # Moderate reversal setup
            elif medium_trend < -0.02:
                return 6  # Continuation in downtrend

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
                return 12  # Very high volume
            elif volume_ratio > 1.5:
                return 8  # High volume
            elif volume_ratio > 1.2:
                return 4  # Moderate volume
            else:
                return 0
        except:
            return 0

    def _calculate_pattern_quality_bonus(self, prev_bar, current_bar):
        """Calcula bonus por calidad del patrón (versión bearish)"""
        bonus = 0

        prev_body_ratio = abs(prev_bar.close - prev_bar.open) / (prev_bar.high - prev_bar.low)
        curr_body_ratio = abs(current_bar.open - current_bar.close) / (current_bar.high - current_bar.low)

        if prev_body_ratio > 0.7 and curr_body_ratio > 0.7:
            bonus += 8  # Both candles have strong bodies
        elif prev_body_ratio > 0.5 and curr_body_ratio > 0.5:
            bonus += 4  # Moderate bodies

        # Gap up opening (more bullish sentiment before reversal)
        if current_bar.open > prev_bar.high:
            bonus += 6  # Gap up opening

        return bonus

    def _calculate_indicator_confluence_bonus(self, current_bar, signal_type):
        """Calcula bonus por confluencia con indicadores técnicos (invertido)"""
        bonus = 0

        try:
            # RSI overbought
            rsi = self.get_indicator_value(current_bar, "rsi_14")
            if rsi and rsi > 65:
                bonus += 8
            elif rsi and rsi > 55:
                bonus += 4

            # Resistance from moving averages
            sma_20 = self.get_indicator_value(current_bar, "sma_20")
            sma_50 = self.get_indicator_value(current_bar, "sma_50")
            current_price = current_bar.close

            if sma_20 and current_price < sma_20 * 1.02:  # Within 2% below SMA20
                bonus += 4
            if sma_50 and current_price < sma_50 * 1.05:  # Within 5% below SMA50
                bonus += 4

            # Bollinger Bands overbought
            bb_upper = self.get_indicator_value(current_bar, "bollinger_upper")
            if bb_upper and current_price > bb_upper * 0.98:  # Near upper band
                bonus += 6

        except:
            pass

        return bonus

    def _calculate_timing_bonus(self, bars):
        """Calcula bonus por timing del patrón"""
        if len(bars) < 10:
            return 0

        # Pattern after consolidation
        recent_ranges = []
        for bar in bars[-10:]:
            daily_range = (bar.high - bar.low) / bar.low
            recent_ranges.append(daily_range)

        avg_range = sum(recent_ranges) / len(recent_ranges)
        current_range = recent_ranges[-1]

        # Pattern during expansion from consolidation
        if current_range > avg_range * 1.5:
            return 8  # Pattern during expansion
        elif avg_range < 0.02:  # Low volatility period
            return 6  # Breakout from low volatility

        return 0

    def _calculate_market_structure_bonus(self, bars, current_price):
        """Calcula bonus por estructura de mercado (versión bearish)"""
        if len(bars) < 15:
            return 0

        # Find recent swing high/low
        highs = [bar.high for bar in bars[-15:]]
        lows = [bar.low for bar in bars[-15:]]

        recent_high = max(highs)
        recent_low = min(lows)

        # Pattern near significant levels
        range_size = recent_high - recent_low

        # Near recent high (potential double top)
        if abs(current_price - recent_high) / range_size < 0.1:
            return 10  # Near significant high

        # Breaking below recent support
        if current_price < recent_low * 1.01:
            return 8  # Breaking support

        return 0

    def _get_symbol_object(self, symbol):
        return Symbol.objects.get(symbol=symbol) if isinstance(symbol, str) else symbol