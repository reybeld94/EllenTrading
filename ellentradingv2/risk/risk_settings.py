from django.db import models

class RiskSettings(models.Model):
    name = models.CharField(max_length=50, default="default", unique=True)

    # Parámetros principales
    risk_pct = models.FloatField(default=0.05)
    min_notional = models.FloatField(default=10)
    conflict_threshold = models.FloatField(default=10)

    # Umbrales de score
    primary_min_score = models.IntegerField(default=60)
    primary_group_avg_score = models.IntegerField(default=50)
    confirm_min_avg_score = models.IntegerField(default=50)
    context_confirm_avg_score = models.IntegerField(default=50)

    # SL/TP/Trailing
    sl_buffer_pct = models.FloatField(default=0.03)
    tp_buffer_pct = models.FloatField(default=0.06)
    trailing_stop_pct = models.FloatField(default=0.02)

    # Pesos por prioridad
    weight_primary = models.FloatField(default=1.0)
    weight_context = models.FloatField(default=0.7)
    weight_confirm = models.FloatField(default=0.5)

    def as_config_dict(self):
        return {
            "risk_pct": self.risk_pct,
            "min_notional": self.min_notional,
            "conflict_threshold": self.conflict_threshold,
            "primary_min_score": self.primary_min_score,
            "primary_group_avg_score": self.primary_group_avg_score,
            "confirm_min_avg_score": self.confirm_min_avg_score,
            "context_confirm_avg_score": self.context_confirm_avg_score,
            "sl_buffer_pct": self.sl_buffer_pct,
            "tp_buffer_pct": self.tp_buffer_pct,
            "trailing_stop_pct": self.trailing_stop_pct,
            "strategy_weights": {
                "Primary": self.weight_primary,
                "Context": self.weight_context,
                "Confirm": self.weight_confirm,
            }
        }

    def __str__(self):
        return f"Risk Settings: {self.name}"
