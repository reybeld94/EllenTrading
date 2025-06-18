from core.models.symbol import Symbol

def calculate_stop_loss(entry_price, sl_percent):
    return entry_price * (1 - sl_percent / 100)

def calculate_take_profit(entry_price, tp_percent):
    return entry_price * (1 + tp_percent / 100)

def percentage_change(entry_price, current_price):
    return ((current_price - entry_price) / entry_price) * 100

def round_price(price, tick_size):
    return round(price / tick_size) * tick_size

from asgiref.sync import sync_to_async

@sync_to_async
def update_live_price(symbol, price):
    symbol_clean = symbol.replace("/", "").upper()  # opcional: normalizar
    try:
        obj = Symbol.objects.get(symbol=symbol_clean)
        obj.live_price = float(price)  # asegurar formato numérico
        obj.save(update_fields=["live_price"])
        print(f"💾 Guardado en BD: {symbol_clean} = {price}")
    except Symbol.DoesNotExist:
        print(f"❌ Symbol {symbol_clean} no existe.")
