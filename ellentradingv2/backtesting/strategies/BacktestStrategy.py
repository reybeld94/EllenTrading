class BacktestStrategy:
    def __init__(self, strategy_instance=None):
        self.strategy_instance = strategy_instance
        self.name = strategy_instance.name if strategy_instance else "Unnamed Strategy"
        self.required_bars = strategy_instance.required_bars if strategy_instance else 50
        self.timeframe = strategy_instance.timeframe if strategy_instance else "1m"
        self.candles = []

    def set_candles(self, candles):
        self.candles = candles

    def should_generate_signal(self, symbol):
        raise NotImplementedError("Debes implementar esto en la subclase.")
