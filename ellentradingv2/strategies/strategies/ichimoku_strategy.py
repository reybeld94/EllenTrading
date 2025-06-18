from signals.signal import Signal
from core.models.enums import SignalType
from core.models.symbol import Symbol
from strategies.base.base_entry import EntryStrategy
from django.utils.timezone import now, timedelta
from asgiref.sync import async_to_sync
from monitoring.utils import log_event


class IchimokuCloudBreakout(EntryStrategy):
    name = "Ichimoku Cloud Breakout"

    def __init__(self, strategy_instance=None):
        self.name = "Ichimoku Cloud Breakout"
        super().__init__(strategy_instance)

    def should_generate_signal(self, symbol: Symbol, execution_mode="simulated", candles=None) -> Signal | None:
        bars = candles or self.get_candles(symbol, execution_mode)

        if len(bars) < self.required_bars:
            return None

        current_bar = bars[-1]
        prev_bar = bars[-2] if len(bars) >= 2 else None
        current_price = current_bar.close

        # Obtener componentes Ichimoku
        ichimoku_data = self._get_ichimoku_values(current_bar, prev_bar)
        if not ichimoku_data:
            return None

        # ✨ CONFIDENCE CON RANGOS UNIVERSALES ESTANDARIZADOS
        # Context strategy: base 35 (puede llegar a 60-80 con bonus)
        confidence = 35  # ⬇️ Ajustado de 65 a 35 para seguir rangos universales (Context priority)
        signal_type = None

        # ✨ MANTENER TODO EL ANÁLISIS ICHIMOKU COMPLETO: Múltiples tipos de señales

        # Signal Type 1: TK Cross (Tenkan-Kijun Cross) - Más común y temprano
        tk_signal, tk_bonus = self._detect_tk_cross(ichimoku_data, current_price)

        # Signal Type 2: Cloud Breakout - Señal fuerte
        cloud_signal, cloud_bonus = self._detect_cloud_breakout(ichimoku_data, current_price, bars)

        # Signal Type 3: Chikou Span confirmation - Confirmación adicional
        chikou_signal, chikou_bonus = self._detect_chikou_confirmation(ichimoku_data, bars)

        # Signal Type 4: Cloud twist/change - Cambio de tendencia de nube
        twist_signal, twist_bonus = self._detect_cloud_twist(ichimoku_data, bars)

        # Signal Type 5: Ichimoku perfect setup - Todas las condiciones alineadas
        perfect_signal, perfect_bonus = self._detect_perfect_setup(ichimoku_data, current_price)

        # Priorizar señales por fuerza (Perfect setup es la más fuerte)
        if perfect_signal:
            signal_type = perfect_signal
            confidence += perfect_bonus
        elif cloud_signal:
            signal_type = cloud_signal
            confidence += cloud_bonus
        elif tk_signal:
            signal_type = tk_signal
            confidence += tk_bonus
        elif twist_signal:
            signal_type = twist_signal
            confidence += twist_bonus
        elif chikou_signal:
            signal_type = chikou_signal
            confidence += chikou_bonus
        else:
            return None

        # ✨ MANTENER TODO EL SISTEMA DE BONUS COMPLETO

        # Bonus 1: Cloud thickness (strength of trend)
        cloud_bonus_extra = self._calculate_cloud_thickness_bonus(ichimoku_data)
        confidence += cloud_bonus_extra

        # Bonus 2: Price position relative to all components
        position_bonus = self._calculate_position_bonus(ichimoku_data, current_price, signal_type)
        confidence += position_bonus

        # Bonus 3: Trend alignment across timeframes (simulated)
        trend_bonus = self._calculate_trend_alignment_bonus(bars, ichimoku_data, signal_type)
        confidence += trend_bonus

        # Bonus 4: Volume confirmation
        volume_bonus = self._calculate_volume_bonus(bars, current_bar)
        confidence += volume_bonus

        # Bonus 5: Momentum confirmation
        momentum_bonus = self._calculate_momentum_bonus(bars, signal_type, current_price)
        confidence += momentum_bonus

        # Bonus 6: Candle pattern confirmation
        candle_bonus = self._calculate_candle_bonus(current_bar, signal_type)
        confidence += candle_bonus

        # Bonus 7: Ichimoku component convergence
        convergence_bonus = self._calculate_convergence_bonus(ichimoku_data)
        confidence += convergence_bonus

        # ✅ APLICAR RANGOS UNIVERSALES
        confidence = min(int(confidence), 100)

        # ✅ THRESHOLD AJUSTADO A RANGOS UNIVERSALES
        # Para Context: 55 (DECENTE alto) mínimo, 70+ (BUENA/FUERTE) preferido
        min_confidence = getattr(self.strategy_instance, "confidence_threshold", 55)
        if confidence < min_confidence:
            return None

        # ✅ OPCIONAL: Log del rango alcanzado
        quality_level = self._get_quality_description(confidence)
        async_to_sync(log_event)(f"📊 Ichimoku Score: {confidence} - {quality_level}",
                                 source='strategies', level='INFO')

        # Evitar duplicados
        symbol_obj = Symbol.objects.get(symbol=symbol) if isinstance(symbol, str) else symbol
        timeframe_minutes = int(self.timeframe.replace("m", "")) if "m" in self.timeframe else 60
        recent_cutoff = now() - timedelta(minutes=timeframe_minutes)
        recent_signal = Signal.objects.filter(
            symbol=symbol_obj,
            signal=signal_type,
            source="ichimoku_cloud",
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
            source="ichimoku_cloud",
            strategy=self.strategy_instance,
            timeframe=self.timeframe
        )
        s.timestamp = getattr(current_bar, "timestamp", getattr(current_bar, "start_time", None))
        s.received_at = s.timestamp

        
        async_to_sync(log_event)(
            f"✅ ICHIMOKU Signal: {signal_type} for {symbol_obj.symbol} | Price: {current_price:.4f} | Cloud: {min(ichimoku_data['span_a'], ichimoku_data['span_b']):.4f}-{max(ichimoku_data['span_a'], ichimoku_data['span_b']):.4f} | Confidence: {confidence}",
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

    def _get_ichimoku_values(self, current_bar, prev_bar):
        """Obtiene todos los valores Ichimoku"""
        try:
            tenkan = self.get_indicator_value(current_bar, "ichimoku_tenkan")
            kijun = self.get_indicator_value(current_bar, "ichimoku_kijun")
            span_a = self.get_indicator_value(current_bar, "ichimoku_span_a")
            span_b = self.get_indicator_value(current_bar, "ichimoku_span_b")
            chikou = self.get_indicator_value(current_bar, "ichimoku_chikou")

            # Valores previos para detectar cambios
            prev_tenkan = self.get_indicator_value(prev_bar, "ichimoku_tenkan") if prev_bar else None
            prev_kijun = self.get_indicator_value(prev_bar, "ichimoku_kijun") if prev_bar else None
            prev_span_a = self.get_indicator_value(prev_bar, "ichimoku_span_a") if prev_bar else None
            prev_span_b = self.get_indicator_value(prev_bar, "ichimoku_span_b") if prev_bar else None

            if None in (tenkan, kijun, span_a, span_b):
                return None

            return {
                'tenkan': tenkan,
                'kijun': kijun,
                'span_a': span_a,
                'span_b': span_b,
                'chikou': chikou,
                'prev_tenkan': prev_tenkan,
                'prev_kijun': prev_kijun,
                'prev_span_a': prev_span_a,
                'prev_span_b': prev_span_b,
                'cloud_top': max(span_a, span_b),
                'cloud_bottom': min(span_a, span_b),
                'prev_cloud_top': max(prev_span_a, prev_span_b) if prev_span_a and prev_span_b else None,
                'prev_cloud_bottom': min(prev_span_a, prev_span_b) if prev_span_a and prev_span_b else None,
            }
        except:
            return None

    def _detect_tk_cross(self, ichimoku_data, current_price):
        """Detecta Tenkan-Kijun crossover"""
        tenkan = ichimoku_data['tenkan']
        kijun = ichimoku_data['kijun']
        prev_tenkan = ichimoku_data['prev_tenkan']
        prev_kijun = ichimoku_data['prev_kijun']

        if not all([prev_tenkan, prev_kijun]):
            return None, 0

        # Bullish TK cross: Tenkan crosses above Kijun
        if prev_tenkan <= prev_kijun and tenkan > kijun:
            bonus = 15
            # Extra bonus if above cloud
            if current_price > ichimoku_data['cloud_top']:
                bonus += 8
            return SignalType.BUY, bonus

        # Bearish TK cross: Tenkan crosses below Kijun
        if prev_tenkan >= prev_kijun and tenkan < kijun:
            bonus = 15
            # Extra bonus if below cloud
            if current_price < ichimoku_data['cloud_bottom']:
                bonus += 8
            return SignalType.SELL, bonus

        return None, 0

    def _detect_cloud_breakout(self, ichimoku_data, current_price, bars):
        """Detecta breakouts de la nube"""
        cloud_top = ichimoku_data['cloud_top']
        cloud_bottom = ichimoku_data['cloud_bottom']
        prev_cloud_top = ichimoku_data['prev_cloud_top']
        prev_cloud_bottom = ichimoku_data['prev_cloud_bottom']

        if len(bars) < 2 or not all([prev_cloud_top, prev_cloud_bottom]):
            return None, 0

        prev_price = bars[-2].close

        # Bullish cloud breakout: Price breaks above cloud
        if prev_price <= prev_cloud_top and current_price > cloud_top:
            bonus = 20
            # Extra bonus if Tenkan > Kijun
            if ichimoku_data['tenkan'] > ichimoku_data['kijun']:
                bonus += 8
            return SignalType.BUY, bonus

        # Bearish cloud breakout: Price breaks below cloud
        if prev_price >= prev_cloud_bottom and current_price < cloud_bottom:
            bonus = 20
            # Extra bonus if Tenkan < Kijun
            if ichimoku_data['tenkan'] < ichimoku_data['kijun']:
                bonus += 8
            return SignalType.SELL, bonus

        return None, 0

    def _detect_chikou_confirmation(self, ichimoku_data, bars):
        """Detecta confirmación del Chikou Span (con fallback si chikou es None)"""
        if len(bars) < 26:
            return None, 0

        chikou = ichimoku_data['chikou']
        price_26_ago = bars[-26].close
        current_price = bars[-1].close

        # ✨ FALLBACK: Si chikou es None, usar análisis de momentum de precio
        if chikou is None:
            async_to_sync(log_event)(f"Chikou is None, using price momentum analysis instead",
                                     source='ichimoku', level='DEBUG')

            # Momentum analysis: current price vs price 26 periods ago
            price_momentum = (current_price - price_26_ago) / price_26_ago

            # Bullish momentum: precio significativamente arriba vs hace 26 períodos
            if price_momentum > 0.03:  # 3%+ gain
                return SignalType.BUY, 8  # Slightly lower bonus since no real chikou
            # Bearish momentum: precio significativamente abajo vs hace 26 períodos
            elif price_momentum < -0.03:  # 3%+ loss
                return SignalType.SELL, 8
            else:
                return None, 0

        # ✅ CHIKOU NORMAL: Si chikou tiene valor, usar lógica original
        # Bullish Chikou: Current price above price 26 periods ago + chikou confirms
        if current_price > price_26_ago and chikou > price_26_ago:
            return SignalType.BUY, 10

        # Bearish Chikou: Current price below price 26 periods ago + chikou confirms
        if current_price < price_26_ago and chikou < price_26_ago:
            return SignalType.SELL, 10

        return None, 0

    def _detect_cloud_twist(self, ichimoku_data, bars):
        """Detecta cambio de color de la nube (twist)"""
        span_a = ichimoku_data['span_a']
        span_b = ichimoku_data['span_b']
        prev_span_a = ichimoku_data['prev_span_a']
        prev_span_b = ichimoku_data['prev_span_b']

        if not all([prev_span_a, prev_span_b]):
            return None, 0

        # Bullish twist: Span A crosses above Span B (green cloud forming)
        if prev_span_a <= prev_span_b and span_a > span_b:
            return SignalType.BUY, 12

        # Bearish twist: Span A crosses below Span B (red cloud forming)
        if prev_span_a >= prev_span_b and span_a < span_b:
            return SignalType.SELL, 12

        return None, 0

    def _detect_perfect_setup(self, ichimoku_data, current_price):
        """Detecta setup perfecto de Ichimoku (todas las condiciones alineadas)"""
        tenkan = ichimoku_data['tenkan']
        kijun = ichimoku_data['kijun']
        cloud_top = ichimoku_data['cloud_top']
        cloud_bottom = ichimoku_data['cloud_bottom']
        chikou = ichimoku_data['chikou']

        # Perfect bullish setup
        bullish_perfect = (
                current_price > cloud_top and  # Price above cloud
                tenkan > kijun and  # Tenkan above Kijun
                tenkan > cloud_top and  # Tenkan above cloud
                kijun > cloud_top  # Kijun above cloud
        )

        # Perfect bearish setup
        bearish_perfect = (
                current_price < cloud_bottom and  # Price below cloud
                tenkan < kijun and  # Tenkan below Kijun
                tenkan < cloud_bottom and  # Tenkan below cloud
                kijun < cloud_bottom  # Kijun below cloud
        )

        if bullish_perfect:
            bonus = 25
            # ✨ CHIKOU BONUS: Solo si chikou no es None
            if chikou is not None and chikou > current_price:
                bonus += 10
                async_to_sync(log_event)(f"Perfect bullish setup with Chikou confirmation",
                                         source='ichimoku', level='INFO')
            elif chikou is None:
                async_to_sync(log_event)(f"Perfect bullish setup (Chikou N/A)",
                                         source='ichimoku', level='INFO')
            return SignalType.BUY, bonus

        if bearish_perfect:
            bonus = 25
            # ✨ CHIKOU BONUS: Solo si chikou no es None
            if chikou is not None and chikou < current_price:
                bonus += 10
                async_to_sync(log_event)(f"Perfect bearish setup with Chikou confirmation",
                                         source='ichimoku', level='INFO')
            elif chikou is None:
                async_to_sync(log_event)(f"Perfect bearish setup (Chikou N/A)",
                                         source='ichimoku', level='INFO')
            return SignalType.SELL, bonus

        return None, 0

    def _calculate_cloud_thickness_bonus(self, ichimoku_data):
        """Calcula bonus basado en grosor de la nube"""
        cloud_thickness = abs(ichimoku_data['span_a'] - ichimoku_data['span_b'])
        cloud_center = (ichimoku_data['span_a'] + ichimoku_data['span_b']) / 2
        thickness_ratio = cloud_thickness / cloud_center

        if thickness_ratio > 0.05:  # Thick cloud (strong trend)
            return 12
        elif thickness_ratio > 0.02:  # Medium cloud
            return 8
        elif thickness_ratio > 0.01:  # Thin cloud
            return 4
        else:
            return 0  # Very thin cloud (weak trend)

    def _calculate_position_bonus(self, ichimoku_data, current_price, signal_type):
        """Calcula bonus basado en posición del precio vs componentes"""
        tenkan = ichimoku_data['tenkan']
        kijun = ichimoku_data['kijun']
        cloud_top = ichimoku_data['cloud_top']
        cloud_bottom = ichimoku_data['cloud_bottom']

        bonus = 0

        if signal_type == SignalType.BUY:
            if current_price > tenkan:
                bonus += 4
            if current_price > kijun:
                bonus += 4
            if current_price > cloud_top:
                bonus += 6
        elif signal_type == SignalType.SELL:
            if current_price < tenkan:
                bonus += 4
            if current_price < kijun:
                bonus += 4
            if current_price < cloud_bottom:
                bonus += 6

        return bonus

    def _calculate_trend_alignment_bonus(self, bars, ichimoku_data, signal_type):
        """Calcula bonus por alineación de tendencia"""
        if len(bars) < 10:
            return 0

        # Simple trend analysis
        price_trend = (bars[-1].close - bars[-10].close) / bars[-10].close
        tenkan_trend = (ichimoku_data['tenkan'] - ichimoku_data['prev_tenkan']) / ichimoku_data['prev_tenkan'] if \
        ichimoku_data['prev_tenkan'] else 0

        # Check if price trend aligns with signal
        if signal_type == SignalType.BUY and price_trend > 0 and tenkan_trend > 0:
            return 8
        elif signal_type == SignalType.SELL and price_trend < 0 and tenkan_trend < 0:
            return 8
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
                return 12
            elif volume_ratio > 1.4:
                return 8
            elif volume_ratio > 1.1:
                return 4
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
        if momentum_strength > 0.03:  # 3%+ momentum
            bonus = 10
        elif momentum_strength > 0.02:  # 2%+ momentum
            bonus = 6
        elif momentum_strength > 0.01:  # 1%+ momentum
            bonus = 3

        # Verify momentum aligns with signal
        if signal_type == SignalType.BUY and price_momentum > 0:
            return bonus
        elif signal_type == SignalType.SELL and price_momentum < 0:
            return bonus
        else:
            return 0

    def _calculate_candle_bonus(self, current_bar, signal_type):
        """Calcula bonus basado en patrón de vela"""
        candle_body = abs(current_bar.close - current_bar.open)
        candle_range = current_bar.high - current_bar.low
        body_ratio = candle_body / candle_range if candle_range > 0 else 0

        if signal_type == SignalType.BUY and current_bar.close > current_bar.open and body_ratio > 0.6:
            return 6  # Strong green candle
        elif signal_type == SignalType.SELL and current_bar.close < current_bar.open and body_ratio > 0.6:
            return 6  # Strong red candle
        else:
            return 0

    def _calculate_convergence_bonus(self, ichimoku_data):
        """Calcula bonus por convergencia de componentes Ichimoku"""
        tenkan = ichimoku_data['tenkan']
        kijun = ichimoku_data['kijun']
        cloud_center = (ichimoku_data['span_a'] + ichimoku_data['span_b']) / 2

        # Check if Tenkan and Kijun are close to each other (potential for strong move)
        tk_distance = abs(tenkan - kijun) / kijun
        if tk_distance < 0.01:  # Very close
            return 8
        elif tk_distance < 0.02:  # Close
            return 4
        else:
            return 0