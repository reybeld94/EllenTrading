from signals.signal import Signal
from core.models.enums import SignalType
from core.models.symbol import Symbol
from strategies.base.base_entry import EntryStrategy
from django.utils.timezone import now, timedelta
import pandas as pd
from monitoring.utils import log_event
from asgiref.sync import async_to_sync


class BollingerBandBreakoutStrategy(EntryStrategy):
    name = "Bollinger Band Breakout"

    def __init__(self, strategy_instance=None, mode="smart"):
        self.name = "Bollinger Band Breakout"
        self.mode = mode  # "smart", "reversal", "breakout"
        super().__init__(strategy_instance)
        self.required_bars = 21

    def should_generate_signal(self, symbol: Symbol, execution_mode="simulated", candles=None) -> Signal | None:
        bars = candles or self.get_candles(symbol, execution_mode)

        if len(bars) < self.required_bars:
            async_to_sync(log_event)(f"[{symbol}] ❌ No hay suficientes velas ({len(bars)}/{self.required_bars})",
                                     source="bollinger", level="DEBUG")
            return None

        last_bar = bars[-1]
        prev_bar = bars[-2] if len(bars) >= 2 else None
        ind = last_bar.indicators

        upper = ind.bollinger_upper
        middle = ind.bollinger_middle
        lower = ind.bollinger_lower
        last_price = last_bar.close

        if any(v is None for v in [upper, middle, lower, last_price]):
            async_to_sync(log_event)(
                f"[{symbol}] ❌ Indicadores incompletos: upper={upper}, middle={middle}, lower={lower}",
                source="bollinger", level="WARNING")
            return None

        # ✨ CONFIDENCE CON RANGOS UNIVERSALES ESTANDARIZADOS
        # Primary strategy: base 40 (puede llegar a 65-85 con bonus)
        confidence = 40  # ⬇️ Ajustado de 65 a 40 para seguir rangos universales (Primary priority)
        signal_type = None

        # ✨ ANÁLISIS DE CONTEXTO DE BANDA COMPLETO
        band_width = (upper - lower) / middle

        # 🔧 FILTRO MEJORADO: Más flexible para banda angosta
        if band_width < 0.005:  # 0.5% en lugar de 1%
            async_to_sync(log_event)(f"[{symbol}] 📉 Banda muy angosta ({band_width:.3%}). Ignorado.",
                                     source="bollinger", level="DEBUG")
            return None

        # Calcular posición relativa del precio en la banda
        band_position = (last_price - lower) / (upper - lower) if upper != lower else 0.5

        # Calcular squeeze state (bandas comprimiéndose)
        if len(bars) >= 5:
            prev_band_width = None
            try:
                prev_upper = bars[-5].indicators.bollinger_upper
                prev_lower = bars[-5].indicators.bollinger_lower
                prev_middle = bars[-5].indicators.bollinger_middle
                if all(v is not None for v in [prev_upper, prev_lower, prev_middle]):
                    prev_band_width = (prev_upper - prev_lower) / prev_middle
            except:
                prev_band_width = None

            is_squeeze = prev_band_width and band_width < prev_band_width * 0.8
        else:
            is_squeeze = False

        # ✨ ANÁLISIS DE TENDENCIA MEJORADO
        # Calcular slope de SMA20 en lugar de Bollinger middle
        sma_slope = 0
        try:
            sma_now = self.get_indicator_value(bars[-1], "sma_20")
            sma_prev = self.get_indicator_value(bars[-5], "sma_20") if len(bars) >= 5 else None
            if sma_now and sma_prev:
                sma_slope = (sma_now - sma_prev) / sma_prev
        except:
            sma_slope = 0

        # ✨ MODO INTELIGENTE: Combina reversal y breakout según contexto
        if self.mode == "smart":
            signal_type, base_confidence = self._smart_analysis(
                last_price, upper, middle, lower, band_position,
                band_width, is_squeeze, sma_slope, bars
            )
            confidence += base_confidence

        elif self.mode == "reversal":
            signal_type, base_confidence = self._reversal_analysis(
                last_price, upper, middle, lower, sma_slope
            )
            confidence += base_confidence

        elif self.mode == "breakout":
            signal_type, base_confidence = self._breakout_analysis(
                last_price, upper, middle, lower, sma_slope
            )
            confidence += base_confidence

        if not signal_type:
            return None

        # ✨ MANTENER TODO EL SISTEMA DE BONUS COMPLETO

        # Bonus 1: Extremidad de posición en banda
        if band_position < 0.1:  # Muy cerca de banda inferior
            confidence += 15
        elif band_position > 0.9:  # Muy cerca de banda superior
            confidence += 15
        elif band_position < 0.2 or band_position > 0.8:
            confidence += 10

        # Bonus 2: Ancho de banda (volatilidad)
        if band_width > 0.04:  # Banda muy ancha (alta volatilidad)
            confidence += 12
        elif band_width > 0.02:  # Banda ancha
            confidence += 8

        # Bonus 3: Post-squeeze expansion
        if is_squeeze and band_width > 0.015:
            confidence += 18  # Expansión después de compresión es muy potente

        # Bonus 4: Confirmación de volumen
        try:
            current_volume = getattr(last_bar, 'volume', None) or self.get_indicator_value(last_bar, "volume")
            if current_volume and len(bars) >= 10:
                volumes = []
                for bar in bars[-10:]:
                    vol = getattr(bar, 'volume', None) or self.get_indicator_value(bar, "volume")
                    if vol:
                        volumes.append(vol)

                if volumes:
                    avg_volume = sum(volumes) / len(volumes)
                    volume_ratio = current_volume / avg_volume

                    if volume_ratio > 2.0:
                        confidence += 15
                    elif volume_ratio > 1.5:
                        confidence += 10
                    elif volume_ratio > 1.2:
                        confidence += 5
        except:
            pass

        # Bonus 5: Confirmación de vela
        if prev_bar:
            prev_price = prev_bar.close
            price_momentum = (last_price - prev_price) / prev_price

            if signal_type == SignalType.BUY and price_momentum > 0.005:  # 0.5% up
                confidence += 8
            elif signal_type == SignalType.SELL and price_momentum < -0.005:  # 0.5% down
                confidence += 8

        # Bonus 6: RSI confirmation
        try:
            rsi = self.get_indicator_value(last_bar, "rsi_14")
            if rsi:
                if signal_type == SignalType.BUY and rsi < 40:  # Oversold
                    confidence += 10
                elif signal_type == SignalType.SELL and rsi > 60:  # Overbought
                    confidence += 10
        except:
            pass

        # ✅ APLICAR RANGOS UNIVERSALES
        confidence = min(int(confidence), 100)

        # ✅ THRESHOLD AJUSTADO A RANGOS UNIVERSALES
        # Para Primary: 50 (DECENTE) mínimo, 65+ (BUENA) preferido
        min_confidence = getattr(self.strategy_instance, "confidence_threshold", 50)
        if confidence < min_confidence:
            async_to_sync(log_event)(
                f"[{symbol}] ⚠️ Confianza {confidence} < umbral mínimo ({min_confidence}). Ignorado.",
                source="bollinger", level="DEBUG")
            return None

        # ✅ OPCIONAL: Log del rango alcanzado
        quality_level = self._get_quality_description(confidence)
        async_to_sync(log_event)(f"📊 Bollinger Score: {confidence} - {quality_level}",
                                 source='strategies', level='INFO')

        # Evitar duplicados
        symbol_obj = Symbol.objects.get(symbol=symbol) if isinstance(symbol, str) else symbol
        timeframe_minutes = int(self.timeframe.replace("m", "")) if "m" in self.timeframe else 60
        recent_cutoff = now() - timedelta(minutes=timeframe_minutes)
        recent_signal = Signal.objects.filter(
            symbol=symbol_obj,
            signal=signal_type,
            source="bollinger_breakout",
            strategy=self.strategy_instance,
            received_at__gte=recent_cutoff
        ).exists()

        if recent_signal:
            async_to_sync(log_event)(f"[{symbol}] ⚠️ Ya existe una señal reciente ({signal_type}). Ignorado.",
                                     source="bollinger", level="DEBUG")
            return None

        # Crear señal
        s = Signal(
            symbol=symbol_obj,
            signal=signal_type,
            price=last_price,
            confidence_score=confidence,
            source="bollinger_breakout",
            strategy=self.strategy_instance,
            timeframe=self.timeframe
        )
        s.timestamp = getattr(bars[-1], "timestamp", getattr(bars[-1], "start_time", None))
        s.received_at = s.timestamp

        async_to_sync(log_event)(
            f"✅ BOLLINGER Signal: {signal_type} for {symbol_obj.symbol} | Price: {last_price:.4f} | Band Pos: {band_position:.1%} | Confidence: {confidence}",
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

    def _smart_analysis(self, price, upper, middle, lower, band_pos, band_width, is_squeeze, slope, bars):
        """Análisis inteligente que decide entre reversal y breakout según contexto"""

        # Si viene de squeeze, favorece breakout
        if is_squeeze and band_width > 0.015:
            if price > upper and slope > 0:
                return SignalType.BUY, 20  # Breakout alcista post-squeeze
            elif price < lower and slope < 0:
                return SignalType.SELL, 20  # Breakout bajista post-squeeze

        # En trending markets, favorece breakout
        if abs(slope) > 0.01:  # Trending
            if price > upper and slope > 0:
                return SignalType.BUY, 15
            elif price < lower and slope < 0:
                return SignalType.SELL, 15

        # En ranging markets, favorece reversal
        else:  # Ranging
            if band_pos < 0.2 and slope > -0.005:  # Cerca de banda inferior, no bajando fuerte
                return SignalType.BUY, 12
            elif band_pos > 0.8 and slope < 0.005:  # Cerca de banda superior, no subiendo fuerte
                return SignalType.SELL, 12

        return None, 0

    def _reversal_analysis(self, price, upper, middle, lower, slope):
        """Análisis de reversión en las bandas"""
        if price < lower and slope > -0.01:  # No debe estar cayendo fuerte
            return SignalType.BUY, 15
        elif price > upper and slope < 0.01:  # No debe estar subiendo fuerte
            return SignalType.SELL, 15
        return None, 0

    def _breakout_analysis(self, price, upper, middle, lower, slope):
        """Análisis de breakout de las bandas"""
        if price > upper and slope > 0:
            return SignalType.BUY, 15
        elif price < lower and slope < 0:
            return SignalType.SELL, 15
        return None, 0