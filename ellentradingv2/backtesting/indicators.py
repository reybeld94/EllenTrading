import pandas as pd
import ta

def calculate_supertrend(df, period=10, multiplier=3):
    hl2 = (df['high'] + df['low']) / 2
    atr = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'], window=period).average_true_range()

    upperband = hl2 + (multiplier * atr)
    lowerband = hl2 - (multiplier * atr)

    supertrend = [True] * len(df)

    for i in range(1, len(df)):
        if df['close'][i] > upperband[i - 1]:
            supertrend[i] = True
        elif df['close'][i] < lowerband[i - 1]:
            supertrend[i] = False
        else:
            supertrend[i] = supertrend[i - 1]

    df['supertrend'] = [1.0 if x else 0.0 for x in supertrend]
    return df

def detect_candlestick_patterns(df):
    df['bullish_engulfing'] = (
        (df['close'].shift(1) < df['open'].shift(1)) &
        (df['close'] > df['open']) &
        (df['close'] > df['open'].shift(1)) &
        (df['open'] < df['close'].shift(1))
    ).astype(float)

    df['bearish_engulfing'] = (
        (df['close'].shift(1) > df['open'].shift(1)) &
        (df['close'] < df['open']) &
        (df['open'] > df['close'].shift(1)) &
        (df['close'] < df['open'].shift(1))
    ).astype(float)

    df['doji'] = (
        (abs(df['close'] - df['open']) <= (df['high'] - df['low']) * 0.1)
    ).astype(float)

    df['hammer'] = (
        ((df['high'] - df['low']) > 3 * abs(df['open'] - df['close'])) &
        ((df[['open', 'close']].min(axis=1) - df['low']) > 2 * abs(df['open'] - df['close']))
    ).astype(float)

    df['shooting_star'] = (
        ((df['high'] - df['low']) > 3 * abs(df['open'] - df['close'])) &
        ((df['high'] - df[['open', 'close']].max(axis=1)) > 2 * abs(df['open'] - df['close']))
    ).astype(float)

    return df

def calculate_all_indicators(df):
    if len(df) < 15:
        print("⚠️ No hay suficientes datos para calcular indicadores (min 15).")
        return pd.DataFrame()
    for p in [9, 10, 20, 21, 50, 55, 100, 200]:
        df[f"sma_{p}"] = df["close"].rolling(window=p).mean()
        df[f"ema_{p}"] = df["close"].ewm(span=p, adjust=False).mean()

    df["wma_10"] = df["close"].rolling(window=10).apply(
        lambda x: sum((i+1)*val for i, val in enumerate(x)) / sum(range(1, 11)), raw=True
    )

    macd = ta.trend.MACD(df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["macd_hist"] = macd.macd_diff()

    adx = ta.trend.ADXIndicator(df["high"], df["low"], df["close"])
    df["adx"] = adx.adx()
    df["plus_di"] = adx.adx_pos()
    df["minus_di"] = adx.adx_neg()

    ichi = ta.trend.IchimokuIndicator(df["high"], df["low"])
    df["ichimoku_tenkan"] = ichi.ichimoku_conversion_line()
    df["ichimoku_kijun"] = ichi.ichimoku_base_line()
    df["ichimoku_span_a"] = ichi.ichimoku_a()
    df["ichimoku_span_b"] = ichi.ichimoku_b()
    df["ichimoku_chikou"] = df["close"].shift(-26)

    df["parabolic_sar"] = ta.trend.PSARIndicator(df["high"], df["low"], df["close"]).psar()

    df["rsi_14"] = ta.momentum.RSIIndicator(df["close"]).rsi()
    stoch = ta.momentum.StochasticOscillator(df["high"], df["low"], df["close"])
    df["stochastic_k"] = stoch.stoch()
    df["stochastic_d"] = stoch.stoch_signal()
    df["cci_20"] = ta.trend.CCIIndicator(df["high"], df["low"], df["close"], window=20).cci()
    df["roc"] = ta.momentum.ROCIndicator(df["close"]).roc()
    df["williams_r"] = ta.momentum.WilliamsRIndicator(df["high"], df["low"], df["close"]).williams_r()
    df["momentum_10"] = df["close"] - df["close"].shift(10)

    atr = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"])
    df["atr_14"] = atr.average_true_range()

    bb = ta.volatility.BollingerBands(df["close"])
    df["bollinger_upper"] = bb.bollinger_hband()
    df["bollinger_middle"] = bb.bollinger_mavg()
    df["bollinger_lower"] = bb.bollinger_lband()

    kelt = ta.volatility.KeltnerChannel(df["high"], df["low"], df["close"])
    df["keltner_upper"] = kelt.keltner_channel_hband()
    df["keltner_lower"] = kelt.keltner_channel_lband()

    df["chaikin_volatility"] = df["high"].rolling(10).std() - df["low"].rolling(10).std()
    df["donchian_upper"] = df["high"].rolling(window=20).max()
    df["donchian_lower"] = df["low"].rolling(window=20).min()

    df["obv"] = ta.volume.OnBalanceVolumeIndicator(df["close"], df["volume"]).on_balance_volume()
    df["ad_line"] = ta.volume.AccDistIndexIndicator(df["high"], df["low"], df["close"], df["volume"]).acc_dist_index()
    df["chaikin_oscillator"] = ta.volume.ChaikinMoneyFlowIndicator(df["high"], df["low"], df["close"], df["volume"]).chaikin_money_flow()
    df["mfi"] = ta.volume.MFIIndicator(df["high"], df["low"], df["close"], df["volume"]).money_flow_index()
    df["volume_sma_20"] = df["volume"].rolling(window=20).mean()
    df["normalized_volume"] = df["volume"] / df["volume"].rolling(window=20).mean()

    df["vwap"] = (df["volume"] * (df["high"] + df["low"] + df["close"]) / 3).cumsum() / df["volume"].cumsum()
    df["slope"] = df["close"].diff()
    df["heikin_ashi_close"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4

    df = calculate_supertrend(df)
    df = detect_candlestick_patterns(df)

    return df
