# core/utils/indicators.py

import pandas as pd
import numpy as np
import ta


def calculate_all_historical_indicators(df: pd.DataFrame, context_label: str = "") -> pd.DataFrame:
    """
    Calcula todos los indicadores técnicos para un DataFrame OHLCV.
    Devuelve el mismo DataFrame con nuevas columnas.
    """
    required_cols = ['open', 'high', 'low', 'close', 'volume']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"[{context_label}] ❌ Falta la columna requerida '{col}'")

    df = df.copy()

    try:
        # SMA y EMA (incluyendo ema_12 y ema_26)
        for period in [9, 10, 12, 20, 21, 26, 50, 55, 100, 200]:
            df[f'sma_{period}'] = df['close'].rolling(window=period).mean()
            df[f'ema_{period}'] = df['close'].ewm(span=period, adjust=False).mean()
    except Exception as e:
        print(f"[{context_label}] ⚠️ Error en cálculo de SMA/EMA: {e}")

    try:
        df['wma_10'] = df['close'].rolling(window=10).apply(lambda x: np.average(x, weights=range(1, 11)), raw=True)
    except Exception as e:
        print(f"[{context_label}] ⚠️ No se pudo calcular WMA: {e}")
        df['wma_10'] = None

    # MACD
    try:
        macd = ta.trend.MACD(df['close'], window_slow=26, window_fast=12, window_sign=9)
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_hist'] = macd.macd_diff()
    except Exception as e:
        print(f"[{context_label}] ⚠️ No se pudo calcular MACD: {e}")

    # ADX y DI
    try:
        adx = ta.trend.ADXIndicator(df['high'], df['low'], df['close'], window=14)
        df['adx'] = adx.adx()
        df['plus_di'] = adx.adx_pos()
        df['minus_di'] = adx.adx_neg()
    except Exception as e:
        print(f"[{context_label}] ⚠️ No se pudo calcular ADX: {e}")

    # RSI
    try:
        df['rsi_14'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
    except Exception as e:
        print(f"[{context_label}] ⚠️ No se pudo calcular RSI: {e}")

    # Estocástico
    try:
        stoch = ta.momentum.StochasticOscillator(df['high'], df['low'], df['close'])
        df['stochastic_k'] = stoch.stoch()
        df['stochastic_d'] = stoch.stoch_signal()
    except Exception as e:
        print(f"[{context_label}] ⚠️ No se pudo calcular Estocástico: {e}")

    # CCI
    try:
        df['cci_20'] = ta.trend.CCIIndicator(df['high'], df['low'], df['close'], window=20).cci()
    except Exception as e:
        print(f"[{context_label}] ⚠️ No se pudo calcular CCI: {e}")

    # ATR (reutilizable)
    try:
        atr = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'], window=14)
        df['atr_14'] = atr.average_true_range()
    except Exception as e:
        print(f"[{context_label}] ⚠️ No se pudo calcular ATR: {e}")
        df['atr_14'] = None

    # Bollinger Bands
    try:
        bb = ta.volatility.BollingerBands(df['close'])
        df['bollinger_upper'] = bb.bollinger_hband()
        df['bollinger_middle'] = bb.bollinger_mavg()
        df['bollinger_lower'] = bb.bollinger_lband()
    except Exception as e:
        print(f"[{context_label}] ⚠️ No se pudo calcular Bollinger Bands: {e}")
        df['bollinger_upper'] = df['bollinger_middle'] = df['bollinger_lower'] = None

    # Donchian Channels
    df['donchian_upper'] = df['high'].rolling(window=20).max()
    df['donchian_lower'] = df['low'].rolling(window=20).min()

    # Keltner Channels
    hlc_mean = (df['high'] + df['low'] + df['close']) / 3
    if 'atr_14' in df and df['atr_14'].isnull().all():
        df['keltner_upper'] = df['keltner_lower'] = None
    else:
        df['keltner_upper'] = hlc_mean + 2 * df['atr_14']
        df['keltner_lower'] = hlc_mean - 2 * df['atr_14']

    # Ichimoku
    try:
        high_9 = df['high'].rolling(window=9).max()
        low_9 = df['low'].rolling(window=9).min()
        df['ichimoku_tenkan'] = (high_9 + low_9) / 2

        high_26 = df['high'].rolling(window=26).max()
        low_26 = df['low'].rolling(window=26).min()
        df['ichimoku_kijun'] = (high_26 + low_26) / 2

        df['ichimoku_span_a'] = ((df['ichimoku_tenkan'] + df['ichimoku_kijun']) / 2).shift(26)

        high_52 = df['high'].rolling(window=52).max()
        low_52 = df['low'].rolling(window=52).min()
        df['ichimoku_span_b'] = ((high_52 + low_52) / 2).shift(26)

        df['ichimoku_chikou'] = df['close'].shift(-26)
    except Exception as e:
        print(f"[{context_label}] ⚠️ No se pudo calcular Ichimoku: {e}")

    # Parabolic SAR
    try:
        psar = ta.trend.PSARIndicator(df['high'], df['low'], df['close'])
        df['parabolic_sar'] = psar.psar()
    except Exception as e:
        print(f"[{context_label}] ⚠️ No se pudo calcular Parabolic SAR: {e}")
        df['parabolic_sar'] = None

    # Momentum, ROC, OBV, MFI
    try:
        df['momentum_10'] = df['close'].diff(periods=10)
        df['roc'] = ta.momentum.ROCIndicator(df['close']).roc()
        df['obv'] = ta.volume.OnBalanceVolumeIndicator(df['close'], df['volume']).on_balance_volume()
        df['mfi'] = ta.volume.MFIIndicator(df['high'], df['low'], df['close'], df['volume']).money_flow_index()
    except Exception as e:
        print(f"[{context_label}] ⚠️ No se pudo calcular momentum/ROC/OBV/MFI: {e}")

    # VWAP
    try:
        df['vwap'] = (df['close'] * df['volume']).cumsum() / df['volume'].cumsum()
    except Exception as e:
        print(f"[{context_label}] ⚠️ No se pudo calcular VWAP: {e}")
        df['vwap'] = None

    # Supertrend y Chaikin Volatility
    df = calculate_supertrend(df)
    df = calculate_chaikin_volatility(df)

    # Candlestick patterns
    df = detect_candlestick_patterns(df)

    # Volumen normalizado
    try:
        df['volume_sma_20'] = df['volume'].rolling(window=20).mean()
        df['normalized_volume'] = (df['volume'] - df['volume_sma_20']) / df['volume'].rolling(window=20).std()
    except Exception as e:
        print(f"[{context_label}] ⚠️ No se pudo calcular volumen normalizado: {e}")
        df['normalized_volume'] = None

    # Slope
    try:
        df['slope'] = df['close'].rolling(window=5).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0], raw=True)
    except Exception as e:
        print(f"[{context_label}] ⚠️ No se pudo calcular slope: {e}")
        df['slope'] = None

    # Heikin Ashi close
    df['heikin_ashi_close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4

    return df



def calculate_supertrend(df: pd.DataFrame, period=10, multiplier=3, context_label="") -> pd.DataFrame:
    df = df.copy()
    required_cols = ['high', 'low', 'close']

    if not all(col in df.columns for col in required_cols):
        print(f"[{context_label}] ❌ Supertrend requiere columnas: {required_cols}")
        df['supertrend'] = None
        return df

    try:
        if 'atr_14' in df and not df['atr_14'].isnull().all():
            atr = df['atr_14']
        else:
            atr = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'], window=period).average_true_range()
    except Exception as e:
        print(f"[{context_label}] ⚠️ No se pudo calcular ATR para Supertrend: {e}")
        df['supertrend'] = None
        return df

    try:
        hl2 = (df['high'] + df['low']) / 2
        upperband = hl2 + multiplier * atr
        lowerband = hl2 - multiplier * atr

        supertrend = [np.nan] * len(df)
        direction = [True] * len(df)  # True = Bullish, False = Bearish

        for i in range(1, len(df)):
            curr_close = df['close'].iloc[i]
            prev_close = df['close'].iloc[i - 1]

            if upperband.iloc[i] < upperband.iloc[i - 1] and prev_close > upperband.iloc[i - 1]:
                upperband.iloc[i] = upperband.iloc[i - 1]

            if lowerband.iloc[i] > lowerband.iloc[i - 1] and prev_close < lowerband.iloc[i - 1]:
                lowerband.iloc[i] = lowerband.iloc[i - 1]

            if direction[i - 1]:
                if curr_close < lowerband.iloc[i]:
                    direction[i] = False
                    supertrend[i] = upperband.iloc[i]
                else:
                    direction[i] = True
                    supertrend[i] = lowerband.iloc[i]
            else:
                if curr_close > upperband.iloc[i]:
                    direction[i] = True
                    supertrend[i] = lowerband.iloc[i]
                else:
                    direction[i] = False
                    supertrend[i] = upperband.iloc[i]

        df['supertrend'] = supertrend
        return df

    except Exception as e:
        print(f"[{context_label}] ⚠️ Error calculando Supertrend: {e}")
        df['supertrend'] = None
        return df



def calculate_chaikin_volatility(df: pd.DataFrame, window=10, context_label="") -> pd.DataFrame:
    df = df.copy()
    required_cols = ['high', 'low']

    if not all(col in df.columns for col in required_cols):
        print(f"[{context_label}] ❌ Chaikin Volatility requiere columnas: {required_cols}")
        df['chaikin_volatility'] = None
        return df

    try:
        hl_range = df['high'] - df['low']
        ema = hl_range.ewm(span=window, adjust=False).mean()
        df['chaikin_volatility'] = ema - ema.shift(window)
    except Exception as e:
        print(f"[{context_label}] ⚠️ No se pudo calcular Chaikin Volatility: {e}")
        df['chaikin_volatility'] = None

    return df




def detect_candlestick_patterns(df):
    df = df.copy()

    try:
        body = abs(df['close'] - df['open'])
        range_total = df['high'] - df['low']
        upper_shadow = df['high'] - df[['close', 'open']].max(axis=1)
        lower_shadow = df[['close', 'open']].min(axis=1) - df['low']

        df['hammer'] = ((body / range_total < 0.3) & (lower_shadow > body * 2)).astype(float)
        df['shooting_star'] = ((body / range_total < 0.3) & (upper_shadow > body * 2)).astype(float)

        df['morning_star'] = 0.0
        df['evening_star'] = 0.0

        if len(df) >= 3:
            for i in range(2, len(df)):
                p1 = df.iloc[i - 2]
                p2 = df.iloc[i - 1]
                p3 = df.iloc[i]

                is_morning = (
                    (p1['close'] < p1['open']) and
                    (abs(p2['close'] - p2['open']) / (p2['high'] - p2['low'] + 1e-6) < 0.1) and
                    (p3['close'] > p3['open']) and
                    (p3['close'] > p1['open'])
                )

                is_evening = (
                    (p1['close'] > p1['open']) and
                    (abs(p2['close'] - p2['open']) / (p2['high'] - p2['low'] + 1e-6) < 0.1) and
                    (p3['close'] < p3['open']) and
                    (p3['close'] < p1['open'])
                )

                if is_morning:
                    df.at[df.index[i], 'morning_star'] = 1.0
                if is_evening:
                    df.at[df.index[i], 'evening_star'] = 1.0

    except Exception as e:
        print(f"⚠️ No se pudieron detectar patrones de velas: {e}")
        df['hammer'] = df['shooting_star'] = df['morning_star'] = df['evening_star'] = None

    return df

