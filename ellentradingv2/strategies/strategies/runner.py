from strategies.base.factory import build_entry_strategies
from core.models.symbol import Symbol
from strategies.models import OpenStrategy
from django.utils.timezone import now
from streaming.websocket.helpers import emit_signal
from risk.risk_manager import RiskManager
import traceback
from django.db import close_old_connections
from monitoring.utils import log_event
from asgiref.sync import async_to_sync

def run_entry_strategies(symbol: Symbol, verbose: bool = True):
    """
    Ejecuta todas las estrategias de entrada para un símbolo específico.
    Usa el timeframe definido por cada estrategia.
    """
    close_old_connections()
    for name, strategy in build_entry_strategies().items():

        try:
            # Asegurarse de que strategy_instance está seteado
            if not strategy.strategy_instance:
                strategy.strategy_instance = OpenStrategy.objects.filter(name=name).first()

            if not strategy.strategy_instance:
                async_to_sync(log_event)(f"❌ Estrategia '{name}' no está registrada en la base de datos",
                    source="strategies", level="ERROR")
                continue

            strategy_timeframe = strategy.strategy_instance.timeframe or "1m"

            signal = strategy.should_generate_signal(symbol, execution_mode="simulated")

            if signal:
                signal.received_at = now()
                signal.save()
                emit_signal(signal)

                if verbose:
                    async_to_sync(log_event)(f"✅ [{name}] Señal generada para {symbol.symbol} en {strategy_timeframe}: {signal.signal} | Score: {signal.confidence_score}",
                              source="strategies", level="INFO")

                rm = RiskManager(symbol.symbol, execution_mode="simulated")
                rm.analyze_and_execute(price=signal.price)


        except Exception as e:
            async_to_sync(log_event)(f"❌ Error en estrategia '{name}' para {symbol.symbol}: {e}",
                      source="strategies", level="ERROR")
            traceback.print_exc()
