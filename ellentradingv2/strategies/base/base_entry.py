from abc import abstractmethod
from signals.signal import Signal
from strategies.models import OpenStrategy
from core.models.symbol import Symbol as SymbolModel
from backtesting.models import HistoricalMarketDataPoint
from core.models.marketdatapoint import MarketDataPoint
import traceback
from monitoring.utils import log_event
from asgiref.sync import async_to_sync

class EntryStrategy:
    def __init__(self, strategy_instance=None):
        self.name = getattr(self, "name", None)
        self.strategy_instance = strategy_instance or self.get_strategy_instance()

        if self.strategy_instance is None:
            async_to_sync(log_event)(f"❌ Strategy instance not found for '{self.name}'. ", source='strategies', level='ERROR')
            raise Exception(f"❌ Strategy instance not found for '{self.name}'. "
                            f"Verifica que exista en OpenStrategy y que esté correctamente nombrada.")

        self.timeframe = self.strategy_instance.timeframe
        self.required_bars = self.strategy_instance.required_bars

    def get_strategy_instance(self):
        try:
            return OpenStrategy.objects.get(name=self.name)
        except OpenStrategy.DoesNotExist:
            async_to_sync(log_event)(f"⚠️ No se encontró estrategia con nombre '{self.name}' en la base de datos.", source='strategies', level='ERROR')
            return None

    def get_indicator_value(self, bar, name: str, fallback_func=None):
        """
        Devuelve el valor del indicador 'name' desde:
        - bar.indicators (si es un dict o JSON)
        - o desde la relación LiveTechnicalIndicator o TechnicalIndicator

        Si no se encuentra, usa fallback_func() si se proporciona.
        """
        timestamp = getattr(bar, 'timestamp', getattr(bar, 'start_time', '???'))

        try:
            indicators = getattr(bar, "indicators", None)

            if isinstance(indicators, dict):
                value = indicators.get(name)
                if value is not None:
                    return value
                async_to_sync(log_event)(f"⚠️ Estrategia: {self.name}, Indicador '{name}' es None en JSON @ {timestamp}",
                          source='strategies', level='WARNING')
                return None

            elif indicators is not None:
                value = getattr(indicators, name, None)
                if value is not None:
                    return value
                async_to_sync(log_event)(f"⚠️ Estrategia: {self.name}, Indicador '{name}' es None en modelo @ {timestamp}",
                          source='strategies', level='WARNING')
                return None

            raise AttributeError("No se encontró 'indicators' en el bar")

        except Exception as e:
            traceback.print_exc()
            async_to_sync(log_event)(f"❌ Estrategia: {self.name}, No se encontró indicador '{name}' para {timestamp}: {e}",
                      source='strategies', level='ERROR')

        if fallback_func:
            return fallback_func()

        return None

    def get_candles(self, symbol, execution_mode: str = "simulated"):
        # 🛡️ Asegurarse de que 'symbol' es una instancia del modelo
        if isinstance(symbol, str):
            symbol = SymbolModel.objects.get(symbol=symbol)

        if not self.timeframe:
            async_to_sync(log_event)(f"Estrategia: {self.name} no tiene timeframe asignado.",
                      source='strategies', level='ERROR')
            raise ValueError(f"⛔ {self.name} no tiene timeframe asignado.")

        if execution_mode == "backtest":
            queryset = HistoricalMarketDataPoint.objects.filter(
                symbol=symbol,
                timeframe=self.timeframe
            ).select_related('indicators').order_by("-timestamp")[:self.required_bars]
        else:
            queryset = MarketDataPoint.objects.filter(
                symbol=symbol,
                timeframe=self.timeframe
            ).select_related('indicators').order_by("-start_time")[:self.required_bars]

        return list(queryset[::-1])  # cronológico




    @abstractmethod
    def should_generate_signal(self, symbol, execution_mode="simulated", candles=None) -> Signal | None:
        pass


