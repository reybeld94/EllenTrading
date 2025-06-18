from backtestingV2.models import HistoricalMarketDataPoint, HistoricalLiveTechnicalIndicator
import pandas as pd

def save_indicators_from_df(df: pd.DataFrame, symbol, timeframe: str):
    for idx, row in df.iterrows():
        start_time = row["time"]
        try:
            point = HistoricalMarketDataPoint.objects.get(symbol=symbol, timeframe=timeframe, start_time=start_time)
            indicators = HistoricalLiveTechnicalIndicator(
                market_data=point,
                **{field.name: row.get(field.name) for field in HistoricalLiveTechnicalIndicator._meta.fields
                   if field.name != "id" and field.name != "market_data"}
            )
            indicators.save()
        except HistoricalMarketDataPoint.DoesNotExist:
            print(f"❌ No se encontró MarketDataPoint para {symbol} @ {start_time}")
        except Exception as e:
            print(f"⚠️ Error al guardar indicadores para {symbol} @ {start_time}: {e}")
