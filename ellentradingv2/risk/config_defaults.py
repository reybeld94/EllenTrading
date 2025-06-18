class RiskConfigDefaults:
    DEFAULTS = {
        "risk_pct": 0.05,
        "min_notional": 10,
        "max_trades_per_symbol": 1,
        "conflict_threshold": 10,
        "primary_min_score": 60,
        "primary_group_avg_score": 50,
        "confirm_min_avg_score": 50,
        "context_confirm_avg_score": 50,
        "sl_buffer_pct": 0.03,
        "tp_buffer_pct": 0.06,
        "trailing_stop_pct": 0.02,
        "strategy_weights": {
            "Primary": 1.0,
            "Context": 0.7,
            "Confirm": 0.5
        }
    }

    @classmethod
    def get(cls, key):
        return cls.DEFAULTS.get(key)

    @classmethod
    def override(cls, custom_config):
        config = cls.DEFAULTS.copy()
        config.update(custom_config or {})
        return config
