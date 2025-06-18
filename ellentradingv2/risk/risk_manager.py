from risk.context import load_risk_context
from risk.decision_engine import resolve_direction, categorize_signals
from risk.signal_scoring import evaluate_categorized
from risk.validation import can_execute_trade
from risk.execution import execute_simulated_trade

class RiskManager:
    def __init__(self, symbol_name, execution_mode="simulated", capital=None, config=None):
        self.symbol_name = symbol_name
        self.execution_mode = execution_mode
        self.config, self.capital, self.signals, self.alpaca = load_risk_context(
            symbol_name, execution_mode, capital_override=capital, config_override=config
        )

    def get_valid_signals(self, current_time=None):
        from core.utils.time import get_active_signals
        from django.utils.timezone import now

        if self.execution_mode == "backtest":
            if current_time is None:
                raise ValueError("❌ En modo backtest debes pasar current_time")
            return get_active_signals(
                self.symbol_name,
                execution_mode="backtest",
                current_time=current_time
            )
        else:
            return get_active_signals(
                self.symbol_name,
                execution_mode=self.execution_mode,
                current_time=now()
            )

    def analyze_and_execute(self, price, current_time=None, verbose=True):

        self.signals = self.get_valid_signals(current_time=current_time)
        direction, filtered_signals, reason = resolve_direction(self.signals, self.config, verbose=verbose)
        if not direction:
            return None

        categorized = categorize_signals(filtered_signals)
        decision = evaluate_categorized(categorized, direction, self.config)
        if not decision["approved"]:
            return None

        signal_to_use = decision["signal"]
        can_exec, size_or_reason = can_execute_trade(
            signal_to_use,
            price,
            self.capital,
            self.config["risk_pct"],
            self.config["min_notional"]
        )
        if not can_exec:
            return None

        if self.execution_mode == "simulated":
            return execute_simulated_trade(signal_to_use, direction, size_or_reason, self.config)

        if self.execution_mode == "backtest":
            from types import SimpleNamespace
            from risk.utils import generate_exit_parameters

            exit_params = generate_exit_parameters(price, direction, self.config)
            return SimpleNamespace(
                symbol=signal_to_use.symbol,
                quantity=size_or_reason["value"] if size_or_reason["mode"] == "qty" else 0,
                notional=size_or_reason["value"] if size_or_reason["mode"] == "notional" else None,
                strategy=signal_to_use.strategy.name if signal_to_use.strategy else None,
                status="BACKTEST",
                price=price,
                direction=direction,
                timestamp=signal_to_use.timestamp,
                timeframe=signal_to_use.timeframe,
                **exit_params
            )

        return None  # live y paper no implementados aún

























# from core.utils.time import get_active_signals
# from alpaca.trading.client import TradingClient
# from core.models.enums import SignalType
# from risk.utils import get_adjusted_confidence
# from streaming.websocket.helpers import emit_trade
# from django.utils.timezone import now
# from types import SimpleNamespace
# from .risk_settings import RiskSettings
# from risk.config_defaults import RiskConfigDefaults
# from trades.logic.portfolio_ops import buy_position, sell_position
# from trades.models.portfolio import Position
#
# ALPACA_API_KEY = "PKALPV6774BZYC8TQ29Q"
# ALPACA_SECRET_KEY = "tUczQ1yDfIQMQzXubtwmpBFiJj8JNZhkMc8gYQaT"
#
# class RiskManager:
#     def __init__(self, symbol_name, execution_mode="simulated", capital=None, config=None):
#         self.symbol_name = symbol_name
#         self.execution_mode = execution_mode
#
#         # ✅ Lógica para cargar config: manual > base de datos > defaults
#         if config:
#             if config is None:
#                 try:
#                     config = RiskSettings.objects.get(pk=1).as_config_dict()
#                 except Exception as e:
#                     print(f"⚠️ No se pudo cargar RiskSettings desde la base de datos: {e}")
#                     config = {}
#
#             self.config = RiskConfigDefaults.override(config)
#
#         else:
#             try:
#                 self.config = RiskSettings.objects.get(name="default").as_config_dict()
#             except RiskSettings.DoesNotExist:
#                 print("⚠️ No se encontró configuración de riesgo en base de datos. Usando defaults.")
#                 self.config = RiskConfigDefaults.override(None)
#
#         # ✅ Guardar parámetros clave como atributos
#         self.risk_pct = self.config["risk_pct"]
#         self.min_notional = self.config["min_notional"]
#         self.conflict_threshold = self.config["conflict_threshold"]
#
#         if execution_mode == "paper":
#             self.alpaca = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)
#             self.capital = self.get_available_capital()
#
#         elif execution_mode == "live":
#             self.alpaca = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=False)
#             self.capital = self.get_available_capital()
#
#         elif execution_mode == "simulated":
#             self.alpaca = None
#             try:
#                 from trades.models.portfolio import Portfolio
#                 self.capital = Portfolio.objects.get(name="Simulado").usd_balance
#             except Portfolio.DoesNotExist:
#                 print("❌ Portafolio 'Simulado' no existe.")
#                 self.capital = 0
#
#         else:
#             self.alpaca = None
#             self.capital = capital if capital is not None else 10_000
#
#         if self.execution_mode != "backtest":
#             self.signals = get_active_signals(
#                 self.symbol_name,
#                 execution_mode=self.execution_mode,
#                 current_time=now()
#             )
#         else:
#             self.signals = []
#
#     #-------------- VALIDATION LAYER-----------------
#     def get_valid_signals(self, current_time=None):
#         if self.execution_mode == "backtest":
#             if current_time is None:
#                 raise ValueError("❌ En modo backtest debes pasar current_time")
#             return get_active_signals(
#                 self.symbol_name,
#                 execution_mode="backtest",
#                 current_time=current_time
#             )
#         else:
#             return get_active_signals(
#                 self.symbol_name,
#                 execution_mode=self.execution_mode,
#                 current_time=now()
#             )
#
# #-------------- STRATEGY PRIORITY LAYER-----------------
#     def categorize_signals(self, signals):
#         categorized = {
#             "Primary": [],
#             "Context": [],
#             "Confirm": []
#         }
#
#         for s in signals:
#             if not s.strategy:
#                 continue
#             prio = s.strategy.priority.title()
#             if prio in categorized:
#                 categorized[prio].append(s)
#
#         return categorized
#
#     def has_consensus(self, signals):
#         directions = set(s.signal for s in signals)
#         return len(directions) == 1
#
#     #metodo revisado
#     def group_signals_by_direction(self):
#         from collections import defaultdict
#         groups = defaultdict(list)
#         print("📦 Agrupando señales por dirección:")
#         for s in self.signals:
#             print(
#                 f"   • {s.symbol.symbol} | {s.signal} | {s.strategy.name if s.strategy else 'Sin estrategia'} | Conf: {s.confidence_score}")
#             groups[s.signal.lower()].append(s)
#         return groups
#
#     def determine_direction_from_conflict(self, signals):
#         weights = self.config.get("strategy_weights", {
#             "Primary": 1.0,
#             "Context": 0.7,
#             "Confirm": 0.5
#         })
#
#         buy_score = 0
#         sell_score = 0
#
#         print("🧮 Calculando scores ponderados:")
#         for s in signals:
#             prio = s.strategy.priority if s.strategy else "???"
#             conf = get_adjusted_confidence(s)
#             strat_score = s.strategy.score if s.strategy and s.strategy.score else 0
#             weight = weights.get(prio, 0.5)
#             total_score = (conf * 0.6 + strat_score * 0.4) * weight
#
#             print(f"   • {s.symbol.symbol} | {s.signal} | {s.strategy.name if s.strategy else 'Sin estrategia'}")
#             print(f"     → Prioridad: {prio} | Confianza: {conf} | Score: {strat_score} | Peso: {weight}")
#             print(f"     → Score total: {total_score:.2f}")
#
#             if s.signal.lower() == SignalType.BUY.lower():
#                 buy_score += total_score
#             elif s.signal.lower() == SignalType.SELL.lower():
#                 sell_score += total_score
#
#         print(f"📊 Scores finales - BUY: {buy_score:.2f} / SELL: {sell_score:.2f}")
#         threshold = self.config.get("conflict_threshold", 10)
#
#         if abs(buy_score - sell_score) < threshold:
#             print(f"⚖️ Diferencia menor que threshold ({threshold}) → Sin decisión")
#             return None, buy_score, sell_score
#         elif buy_score > sell_score:
#             return "BUY", buy_score, sell_score
#         elif sell_score > buy_score:
#             return "SELL", buy_score, sell_score
#         else:
#             return None, buy_score, sell_score
#
#     def resolve_direction(self):
#         print("🔍 Resolviendo dirección basada en señales activas...")
#
#         if self.has_consensus(self.signals):
#             direction = self.signals[0].signal
#             print(f"✅ Consenso detectado: {direction}")
#             return direction, self.signals, "Consensus found among all signals"
#
#         grouped = self.group_signals_by_direction()
#
#         direction, buy_score, sell_score = self.determine_direction_from_conflict(self.signals)
#
#         if direction:
#             filtered_signals = grouped.get(direction.lower(), [])
#             print(f"✅ Dirección resuelta por scores: {direction}")
#             return direction, filtered_signals, f"Conflict resolved: BUY={buy_score:.2f} / SELL={sell_score:.2f}"
#
#         print("❌ No se pudo determinar una dirección clara.")
#         return None, [], "No dominant direction could be determined"
#
#     #--------------SCORING & WEIGHTING LAYER-----------------
#     # def evaluate_categorized(self, categorized, direction):
#     #     """
#     #     Versión permisiva: permite trades con señales individuales o combinaciones suaves.
#     #     """
#     #     print(categorized)
#     #
#     #     def avg_weighted(signals):
#     #         if not signals:
#     #             return 0
#     #         return sum(self.weighted_score(s) for s in signals) / len(signals)
#     #
#     #     # 🟢 REGLA 1: Cualquier PRIMARY con score >= 40 ejecuta sola
#     #     if categorized["Primary"]:
#     #         best = max(categorized["Primary"], key=self.weighted_score)
#     #         if self.weighted_score(best) >= 40:
#     #             return {
#     #                 "approved": True,
#     #                 "action": direction,
#     #                 "reason": f"Primary '{best.strategy.name}' ejecuta sola con score {self.weighted_score(best):.2f}",
#     #                 "signal": best
#     #             }
#     #
#     #     # 🟢 REGLA 2: Cualquier CONTEXT con score >= 65 ejecuta sola
#     #     if categorized["Context"]:
#     #         best = max(categorized["Context"], key=self.weighted_score)
#     #         if self.weighted_score(best) >= 40:
#     #             return {
#     #                 "approved": True,
#     #                 "action": direction,
#     #                 "reason": f"Context '{best.strategy.name}' ejecuta sola con score {self.weighted_score(best):.2f}",
#     #                 "signal": best
#     #             }
#     #
#     #     # 🟢 REGLA 3: Cualquier CONFIRM con score >= 70 ejecuta sola
#     #     if categorized["Confirm"]:
#     #         best = max(categorized["Confirm"], key=self.weighted_score)
#     #         if self.weighted_score(best) >= 40:
#     #             return {
#     #                 "approved": True,
#     #                 "action": direction,
#     #                 "reason": f"Confirm '{best.strategy.name}' ejecuta sola con score {self.weighted_score(best):.2f}",
#     #                 "signal": best
#     #             }
#     #
#     #     # 🟢 REGLA 4: Cualquier combinación de 2 señales (aunque sean de bajo peso) con avg >= 55
#     #     combined = categorized["Primary"] + categorized["Context"] + categorized["Confirm"]
#     #     if len(combined) >= 2:
#     #         avg_score = avg_weighted(combined)
#     #         if avg_score >= 40:
#     #             return {
#     #                 "approved": True,
#     #                 "action": direction,
#     #                 "reason": f"Combinación permisiva ejecuta (avg score {avg_score:.2f})",
#     #                 "signal": combined[0]
#     #             }
#     #
#     #     # ❌ FINAL: No se aprueba
#     #     return {
#     #         "approved": False,
#     #         "reason": f"Permisive mode: no signal met the relaxed thresholds"
#     #     }
#
#     def evaluate_categorized(self, categorized, direction):
#         """
#         Evalúa si las señales (ya filtradas en una sola dirección) tienen el peso suficiente
#         para justificar un trade. Aplica reglas específicas según prioridad y score.
#         """
#         # print(categorized)
#         def avg_weighted(signals):
#             if not signals:
#                 return 0
#             return sum(self.weighted_score(s) for s in signals) / len(signals)
#
#         # ----------- REGLA 1: PRIMARY fuerte ejecuta sola ------------
#         if categorized["Primary"]:
#             best = max(categorized["Primary"], key=self.weighted_score)
#             if self.weighted_score(best) >= self.config.get("primary_min_score", 50):
#                 return {
#                     "approved": True,
#                     "action": direction,
#                     "reason": f"Primary '{best.strategy.name}' approved with score {self.weighted_score(best):.2f}",
#                     "signal": best
#                 }
#
#
#         # ----------- REGLA 2: CONTEXT + CONFIRM con promedio decente ------------
#         if categorized["Context"] and categorized["Confirm"]:
#             combined = categorized["Context"] + categorized["Confirm"]
#             if len(combined) >= 2:
#                 avg_score = avg_weighted(combined)
#                 if avg_score >= self.config.get("context_confirm_avg_score", 50):
#                     return {
#                         "approved": True,
#                         "action": direction,
#                         "reason": f"Context + Confirm aligned (avg score {avg_score:.2f})",
#                         "signal": combined[0]
#                     }
#
#         # ----------- REGLA 3: 3+ CONFIRM con buen score ------------
#         if len(categorized["Confirm"]) >= 3:
#             avg_score = avg_weighted(categorized["Confirm"])
#             if avg_score >= self.config.get("confirm_min_avg_score", 50):
#                 return {
#                     "approved": True,
#                     "action": direction,
#                     "reason": f"3 Confirm signals aligned (avg score {avg_score:.2f})",
#                     "signal": categorized["Confirm"][0]
#                 }
#
#         # REGLA 4 (opcional): 2+ Primary con promedio >= 78
#         if len(categorized["Primary"]) >= 2:
#             avg_score = avg_weighted(categorized["Primary"])
#             if avg_score >= self.config.get("primary_group_avg_score", 50):
#                 return {
#                     "approved": True,
#                     "action": direction,
#                     "reason": f"2+ Primary strategies aligned (avg score {avg_score:.2f})",
#                     "signal": categorized["Primary"][0]
#                 }
#
#
#         # ----------- REGLA FINAL: No se aprueba ------------
#         return {
#             "approved": False,
#             "reason": f"Signals in '{direction}' direction do not meet minimum scoring requirements"
#         }
#
#     def weighted_score(self, signal):
#         """
#         Calcula el score ponderado de una señal según confianza y score de estrategia.
#         """
#         prio_weights = self.config.get("strategy_weights", {"Primary": 1.0, "Context": 0.7, "Confirm": 0.5})
#
#         prio = signal.strategy.priority.title() if signal.strategy else "Confirm"
#         conf = signal.confidence_score or 0
#         strat_score = signal.strategy.score if signal.strategy and signal.strategy.score else 0
#         weight = prio_weights.get(prio, 0.5)
#
#         return (conf * 0.6 + strat_score * 0.4) * weight
#
#     #---------------------------- CAPITAL & EXPOSURE LAYER -------------------------------
#
#     def is_symbol_already_in_position(self, symbol):
#         """
#         Verifica si ya existe un trade abierto para este símbolo.
#         """
#         from trades.models import Trade
#         return Trade.objects.filter(symbol=symbol, status="EXECUTED").exists()
#
#     def is_crypto(self, symbol):
#         """
#         Detecta si el activo pertenece al mercado cripto usando asset_class.
#         """
#         return symbol.asset_class == "crypto"
#
#     def calculate_position_size(self, price, symbol):
#         capital = self.capital
#         max_allocation = capital * self.risk_pct
#
#
#         if self.is_crypto(symbol):
#             # Cripto: siempre usar notional
#             notional = min(max_allocation, capital)
#             return {"mode": "notional", "value": round(notional, 2)}
#
#         # Acciones: usar qty si alcanza, sino usar notional
#         qty = int(max_allocation // price)
#         if qty >= 1:
#             return {"mode": "qty", "value": qty}
#         else:
#             return {"mode": "notional", "value": round(max_allocation, 2)}
#
#     def can_execute_trade(self, signal, price):
#         """
#         Evalúa si se puede ejecutar el trade según:
#         - Capital disponible
#         - Posiciones abiertas
#         - Tamaño mínimo requerido
#         """
#         symbol = signal.symbol
#
#         if self.is_symbol_already_in_position(symbol):
#             return False, "Already in position for this symbol"
#
#         size = self.calculate_position_size(price, symbol)
#
#         if size["mode"] == "qty" and size["value"] <= 0:
#             return False, "Insufficient capital for minimum qty"
#
#         if size["mode"] == "notional" and size["value"] < self.min_notional:
#             return False, f"Minimum notional too small (below ${self.min_notional})"
#
#         return True, size
#
# #----------------------------  EXECUTION AUTHORIZATION LAYER -------------------------------
#
#     def execute_trade(self, signal, direction, size, price):
#         """
#         Ejecuta un trade según el modo: simulated (DB), paper (simulado externo), live (real)
#         """
#         from trades.models.trade import Trade
#         from django.utils.timezone import now
#         from risk.utils import generate_exit_parameters
#
#         if self.execution_mode == "paper":
#             from alpaca.trading.requests import MarketOrderRequest, StopLossRequest, TakeProfitRequest
#             from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass
#
#             try:
#                 symbol = signal.symbol.symbol.replace("/", "")
#                 side = OrderSide.BUY if direction.lower() == "buy" else OrderSide.SELL
#                 qty = size["value"] if size["mode"] == "qty" else None
#                 notional = size["value"] if size["mode"] == "notional" else None
#
#                 # 📈 Calcula precios objetivo (ajusta a tu lógica de riesgo real)
#                 entry_price = price  # puede ser el último precio del market data
#                 stop_pct = 0.03  # -3%
#                 tp_pct = 0.06  # +6%
#
#                 stop_price = round(entry_price * (1 - stop_pct), 2) if side == OrderSide.BUY else round(
#                     entry_price * (1 + stop_pct), 2)
#                 tp_price = round(entry_price * (1 + tp_pct), 2) if side == OrderSide.BUY else round(
#                     entry_price * (1 - tp_pct), 2)
#
#                 print(f"🧮 Entry: {entry_price} | TP: {tp_price} | SL: {stop_price}")
#
#                 # 📤 Crea orden bracket
#                 order_data = MarketOrderRequest(
#                     symbol=symbol,
#                     qty=qty,
#                     notional=notional,
#                     side=side,
#                     time_in_force=TimeInForce.DAY,
#                     order_class=OrderClass.BRACKET,
#                     take_profit=TakeProfitRequest(limit_price=tp_price),
#                     stop_loss=StopLossRequest(stop_price=stop_price)
#                 )
#
#                 order = self.alpaca.submit_order(order_data)
#                 Trade.objects.create(
#                     symbol=signal.symbol,
#                     entry_price=price,
#                     quantity=qty or 0,
#                     notional=notional,
#                     strategy=signal.strategy,
#                     direction=direction.upper(),
#                     status="OPEN",  # o "PENDING" si prefieres hasta que cierre el TP/SL
#                     notes="Trade enviado a Alpaca en modo PAPER con bracket.",
#                     entry_time=now()
#                 )
#                 print(f"✅ BRACKET order enviada: {order.id} → {symbol} {side.name}")
#
#                 return type("PaperTrade", (), {
#                     "symbol": signal.symbol,
#                     "quantity": qty,
#                     "notional": notional,
#                     "strategy": signal.strategy.name if signal.strategy else None,
#                     "status": "PAPER",
#                     "order_id": order.id,
#                     "tp_price": tp_price,
#                     "stop_price": stop_price
#                 })()
#
#             except Exception as e:
#                 print(f"❌ Error en BRACKET order PAPER: {e}")
#                 return None
#
#         elif self.execution_mode == "live":
#             # 🚨 Para el futuro: conectar con broker real como Alpaca
#             print("⚠️ LIVE execution not yet implemented.")
#             return None
#
#         elif self.execution_mode == "backtest":
#             exit_params = generate_exit_parameters(price, direction)
#             return SimpleNamespace(
#                 symbol=signal.symbol,
#                 quantity=size["value"] if size["mode"] == "qty" else 0,
#                 notional=size["value"] if size["mode"] == "notional" else None,
#                 strategy=signal.strategy.name if signal.strategy else None,
#                 status="BACKTEST",
#                 price=price,
#                 direction=direction,
#                 timestamp=signal.timestamp,
#                 timeframe=signal.timeframe,
#                 **exit_params
#             )
#
#
#         elif self.execution_mode == "simulated":
#             # ✅ Validación: asegurarse de que se pueda modificar el portafolio
#             try:
#                 if direction.lower() == "buy":
#                     buy_position("Simulado", signal.symbol.symbol, size["value"])
#                     price = signal.symbol.live_price
#                     qty = round(size["value"] / price, 6) if size["mode"] == "notional" else size["value"]
#                 else:
#                     if not Position.objects.filter(portfolio__name="Simulado", symbol=signal.symbol).exists():
#                         print(f"❌ No hay posición abierta para {signal.symbol.symbol}. Abortando SELL.")
#                         return None
#                     sell_position("Simulado", signal.symbol.symbol)
#                     # 💥 Aquí faltaba definir qty en el caso de SELL también
#                     qty = round(size["value"] / price, 6) if size["mode"] == "notional" else size["value"]
#
#             except Exception as e:
#                 print(f"❌ Error al modificar el portafolio: {e}")
#                 return None
#
#             trade_data = {
#                 "symbol": signal.symbol,
#                 "direction": direction.lower(),
#                 "price": price,
#                 "execution_mode": self.execution_mode,
#                 "confidence_score": int(signal.confidence_score),
#                 "strategy": signal.strategy.name if signal.strategy else None,
#                 "notes": f"Auto-executed from strategy '{signal.strategy.name}'" if signal.strategy else "",
#                 "status": "EXECUTED",
#                 "executed_at": now(),
#                 "quantity": qty,
#                 "filled_quantity": qty,
#                 "notional": size["value"] if size["mode"] == "notional" else None,
#                 "filled_notional": size["value"] if size["mode"] == "notional" else None,
#             }
#
#             trade_data.update(generate_exit_parameters(price, direction))
#
#             trade = Trade.objects.create(**trade_data)
#             trade.triggered_by.add(signal)
#             emit_trade(trade)
#             return trade
#
#         else:
#             raise ValueError(f"❌ Unknown execution mode: {self.execution_mode}")
#
#     def analyze_and_execute(self, price, verbose=True):
#
#
#         # if verbose:
#         #     print(f"\n🔍 Iniciando análisis de riesgo para: {self.symbol_name}")
#         #     print("📡 Buscando señales activas...")
#
#         self.signals = self.get_valid_signals()
#
#         #DETERMINAR DIRECCION BASADO EN MI SISTEMA DE SCORING
#         direction, filtered_signals, reason = self.resolve_direction()
#         # if verbose:
#             # print(f"🎯 Dirección determinada: {direction or 'Ninguna'}")
#             # print(f"🧠 Justificación: {reason}")
#         if not direction:
#             # if verbose:
#             #     print("❌ No se puede proceder sin dirección clara.")
#             return None
#
#         categorized = self.categorize_signals(filtered_signals)
#         decision = self.evaluate_categorized(categorized, direction)
#
#         if not decision["approved"]:
#             # if verbose:
#             #     print("⛔ Trade rechazado:", decision["reason"])
#             return None
#
#         signal_to_use = decision["signal"]
#         # if verbose:
#         #     print(f"✅ Señal aprobada: {signal_to_use.strategy.name}")
#         #     print(f"➡️ Acción: {decision['action']}")
#         #     print("🧮 Calculando tamaño de posición...")
#
#         can_exec, size_or_reason = self.can_execute_trade(signal_to_use, price)
#
#         if not can_exec:
#             # if verbose:
#             #     print("🚫 No se puede ejecutar trade:", size_or_reason)
#             return None
#
#         # if verbose:
#         #     print(f"📦 Tamaño calculado: {size_or_reason}")
#         #     print("🚀 Ejecutando trade en base de datos...")
#
#         trade = self.execute_trade(signal_to_use, direction, size_or_reason, price)
#
#
#
#         # if verbose:
#         #     print("✅ Trade creado con éxito:")
#         #     print(f"   📈 Symbol: {trade.symbol}")
#         #     print(f"   📊 Qty: {trade.quantity}")
#         #     print(f"   💰 Notional: {trade.notional}")
#         #     print(f"   ⚙️ Strategy: {trade.strategy}")
#         #     print(f"   📌 Status: {trade.status}\n")
#
#         return trade
